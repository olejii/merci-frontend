# Data dictionary и модель импорта

Ниже приведены поля предоставленных CSV и правила их импорта. CSV — историческая схема задания. Текущая модель приложения принимает чаевые без суммы блюд: поля, которых нет в модели нового продукта, сохраняются в JSON `source_metadata.row`, но не участвуют в расчёте платежа.

В этих таблицах «Ошибка» означает причину CLI-валидации, а не HTTP-код: импортёр сообщает имя файла/строки и прерывает транзакцию при нарушении.

## `merchants.csv`

| Поле | Тип | Обяз. | Ограничение | Пример | Ошибка |
|---|---|---|---|---|---|
| `merchant_id` | string | Да | `m_NNN`, уникальный PK | `m_001` | `INVALID_CSV` |
| `name` | string | Да | 1–100 символов | `Вкус-Сервис Тверская` | `INVALID_CSV` |
| `status` | enum | Да | `PENDING`, `ACTIVE`, `BLOCKED` | `ACTIVE` | `INVALID_CSV` |
| `description` | string | Нет | 0–200 символов | `Ресторан сети, Тверская` | `INVALID_CSV` |

## `employees.csv`

| Поле | Тип | Обяз. | Ограничение | Пример | Ошибка |
|---|---|---|---|---|---|
| `employee_id` | string | Да | `e_NNN`, уникальный PK | `e_001` | `INVALID_CSV` |
| `merchant_id` | string | Да | FK на существующий мерчант | `m_001` | `UNKNOWN_MERCHANT` |
| `name` | string | Да | 1–100 символов | `Иванов И.` | `INVALID_CSV` |
| `payment_details` | string | Да | Только маска `****NNNN` | `****1001` | `INVALID_PAYMENT_DETAILS` |

Номер телефона, email, роль и активный пользователь берутся из актуальной модели приложения; в старом CSV их нет. Для импортированных записей создаётся служебный email `employee_id@import.invalid`, пользователь не активируется.

## `qr_links.csv`

| Поле | Тип | Обяз. | Ограничение | Пример | Ошибка |
|---|---|---|---|---|---|
| `qr_id` | string | Да | Уникальный идентификатор `qr_*` | `qr_001` | `INVALID_CSV` |
| `merchant_id` | string | Да | FK на мерчант | `m_001` | `UNKNOWN_MERCHANT` |
| `employee_id` | string | Да | FK на сотрудника того же мерчанта | `e_001` | `UNKNOWN_EMPLOYEE` |
| `receipt_id` | string | Да в источнике | Legacy-поле; не используется продуктом | `r_1001` | `INVALID_CSV` |
| `nonce` | string | Да | 6 hex, уникальный | `c82561` | `INVALID_NONCE` |
| `exp` | ISO-8601 datetime | Да | Дата/время с timezone | `2025-11-01T23:59:00Z` | `INVALID_DATETIME` |
| `signature` | string | Да в источнике | 16 hex; исходная подпись сохраняется как архивная | `68d0f361ac38c12b` | `INVALID_SIGNATURE` |

При создании живого QR подпись пересчитывается под `TIP_QR_SECRET` по текущему payload `merchant|employee|nonce|exp`; исходная legacy-подпись не принимается как действительная. Значение `receipt_id` сохраняется только для трассировки источника.

## `payments.csv`

| Поле | Тип | Обяз. | Ограничение | Пример | Ошибка |
|---|---|---|---|---|---|
| `payment_id` | string | Да | `p_NNNN`, уникальный PK | `p_0001` | `INVALID_CSV` |
| `merchant_id` | string | Да | FK на мерчант | `m_001` | `UNKNOWN_MERCHANT` |
| `employee_id` | string | Да | FK на сотрудника того же мерчанта | `e_001` | `UNKNOWN_EMPLOYEE` |
| `amount` | decimal | Да в источнике | Положительная сумма чека legacy; только metadata | `637.00` | `INVALID_AMOUNT` |
| `tip` | decimal | Да | Положительная сумма, ≤ 1 000 000 ₽, две копейки | `31.85` | `TIP_OUT_OF_RANGE` |
| `status` | enum | Да | `CREATED`, `PENDING`, `SUCCESS`, `DECLINED`, `CANCELED` | `SUCCESS` | `INVALID_STATUS` |
| `timestamp` | ISO-8601 datetime | Да | Дата/время с timezone | `2025-11-01T18:00:00Z` | `INVALID_DATETIME` |

`amount` не переносится в платёжную модель и не используется в отчётности/сумме списания. Для каждой строки платёж связывается с QR по цифровому суффиксу ID (`p_0001` ↔ `qr_001`).

## Модель приложения и связи

| Сущность | Ключевые данные и связи |
|---|---|
| `Merchant` | PK `merchant_id`, владелец, название, статус, описание; 1:N к сотрудникам, QR и платежам |
| `Employee` | PK `employee_id`, FK `merchant`, пользователь, роль, email, телефон, маска выплаты; 1:N к QR, целям и платежам |
| `QRLink` | PK `qr_id`, FK на мерчанта и сотрудника, уникальный nonce, expires_at, HMAC, used_at; 1:N попыток в общем случае |
| `Payment` | PK `payment_id`, FK на QR/мерчанта/сотрудника/цель, tip, service fee, способ оплаты, опциональные отзывы/рейтинги, статус и idempotency key |
| `TipGoal` | PK `goal_id`, FK на сотрудника, целевая сумма; collected вычисляется из успешных платежей |
| `TipReport` | FK на мерчанта и диапазон дат; агрегаты чаевых и успешности, уникально на мерчанта/период |
| `AuditEvent` | событие платежа и QR, действие, старый/новый статус, сумма, actor, время и JSON details |
| `UserProfile` | One-to-one с пользователем, email до 254 символов (case-insensitive unique), уникальный телефон E.164 |

Схема импортируется командой `manage.py import_seed_csv --dry-run`; обычный запуск — только после успешной проверки. Команда не обновляет записи с уже занятыми PK, валидирует FK и использует транзакцию. См. `tasks/12_отчет_проверок.md`.
