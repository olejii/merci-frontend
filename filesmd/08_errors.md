# ER-модель и ограничения данных

## Сущности

| Сущность | Назначение |
|---|---|
| `Merchant` | Заявка/заведение и владелец |
| `Employee` | Сотрудник мерчанта с ролью и маской выплаты |
| `QRLink` | Подписанная одноразовая ссылка на чаевые |
| `Payment` | Платёж чаевых с состоянием и идемпотентностью |
| `TipReport` | Вычисленные агрегаты по мерчанту и датам |
| `AuditEvent` | След действий и переходов платежа |

Дополнительные сущности приложения: `UserProfile` (контакты), `TipGoal` (цели сбора).

## Атрибуты и ключи

| Сущность | Поле | Тип | PK/FK | Обяз. | Ограничение |
|---|---|---|---|---|---|
| Merchant | `merchant_id` | string | PK | Да | `m_NNN` |
| Merchant | `name` | string | — | Да | 1–100 |
| Merchant | `status` | enum | — | Да | `PENDING/ACTIVE/BLOCKED` |
| Merchant | `description` | string | — | Нет | до 200 |
| Employee | `employee_id` | string | PK | Да | `e_NNN` |
| Employee | `merchant_id` | string | FK → Merchant | Да | существующий мерчант |
| Employee | `user_id` | integer | FK → User | Нет до принятия invite | unique |
| Employee | `email`, `phone`, `name`, `role` | string | — | email/name/role да | email до 254; телефон E.164; роли WAITER/BARTENDER/HOSTESS |
| Employee | `payment_details` | string | — | Да | только `****NNNN` |
| QRLink | `qr_id` | string | PK | Да | `qr_*` |
| QRLink | `merchant_id`, `employee_id` | string | FK | Да | Employee принадлежит Merchant |
| QRLink | `nonce` | string | unique | Да | 6 lowercase hex |
| QRLink | `expires_at` | datetime | — | Да | timezone-aware, TTL 24h при создании |
| QRLink | `signature` | string | — | Да | 16 lowercase hex, HMAC |
| QRLink | `used_at` | datetime | — | Нет | выставляется при создании платежа |
| Payment | `payment_id` | string | PK | Да | `p_NNNN` |
| Payment | `qr_id`, `merchant_id`, `employee_id` | string | FK | Да | ссылки на связанные записи |
| Payment | `tip` | decimal | — | Да | >0 и ≤1 000 000, 2 знака |
| Payment | `service_fee` | decimal | — | Да | только 0.00 или 25.00 |
| Payment | `status` | enum | — | Да | CREATED/PENDING/SUCCESS/DECLINED/CANCELED |
| Payment | `idempotency_key` | string | unique per merchant | Да | 16–128 символов |
| TipReport | `merchant_id` | string | FK → Merchant | Да | период start/end; один отчёт на период |
| TipReport | `tips_total`, `avg_tip_amount`, `success_rate` | decimal | — | Да | агрегаты успешных операций |
| AuditEvent | `event_id` | string | PK | Да | уникальный ID |
| AuditEvent | `payment_id`, `qr_id` | string | FK | Да | существующие записи |
| AuditEvent | `action`, `from_status`, `to_status`, `actor`, `at`, `amount_total`, `details` | mix | — | Да | actor из system/client/officer/merchant/admin |

Сумма чека, `receipt_id` и `tip_pct` в актуальную схему Payment/QR не входят. При импорте исходных CSV их исходные значения остаются в JSON metadata и не включаются в расчёты.

## Кардинальности

| Связь | Тип | Обоснование |
|---|---|---|
| Merchant → Employee | 1:N | Заведение имеет много сотрудников |
| Merchant → QRLink | 1:N | QR выписываются сотрудникам одного заведения |
| Employee → QRLink | 1:N | Сотрудник может создавать новые ссылки |
| QRLink → Payment | 1:N логически | Повтор с тем же ключом возвращает один Payment; разные попытки могут ссылаться на QR до использования, успешное создание фиксирует `used_at` |
| Merchant → TipReport | 1:N | Один агрегат на каждый период |
| Payment → AuditEvent | 1:N | Каждое состояние/действие имеет отдельное событие |
| Employee → TipGoal | 1:N | Сотрудник может вести несколько целей |
| User → UserProfile | 1:1 | Контактный профиль учётной записи |

Из-за одноразового `used_at` новый запрос с новым ключом по использованному QR отклоняется. Реляционная модель допускает несколько audit-событий на Payment.

## Основные API-коды ошибок

| Код | HTTP | Значение |
|---|---:|---|
| `INVALID_QR` | 404 / 422 | QR не найден или подпись некорректна |
| `QR_EXPIRED` | 410 | Срок QR истёк; для нового платежа нужен новый QR |
| `QR_USED` | 409 | QR уже использован |
| `MERCHANT_BLOCKED` | 403 | Мерчант не имеет статуса `ACTIVE` |
| `TIP_OUT_OF_RANGE` | 422 | Сумма чаевых недопустима |
| `PAYMENT_METHOD_INVALID` | 422 | Метод оплаты не входит в справочник |
| `IDEMPOTENCY_KEY_REQUIRED` | 422 | Ключ отсутствует или вне длины 16–128 |
| `IDEMPOTENCY_CONFLICT` | 409 | Тот же ключ предъявлен с другим payload |
| `CANCEL_NOT_ALLOWED` | 409 | Отмена не разрешена для текущего статуса |
| `INVALID_PERIOD` | 422 | Неверный или слишком длинный отчётный период |
| `FORBIDDEN` | 403 | Роль/пользователь не имеет доступа к данным |

Ошибки CLI-импортёра не являются HTTP API: команда завершает транзакцию и печатает `filename:line: reason` как `CommandError`.
