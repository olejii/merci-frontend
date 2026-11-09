from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    email = models.EmailField(max_length=254)
    phone = models.CharField(
        max_length=16,
        unique=True,
        validators=[RegexValidator(r"^\+[1-9][0-9]{7,14}$", "Введите телефон в формате +79991234567.")],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="unique_userprofile_email_ci"),
        ]


class Merchant(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Ожидает проверки"
        ACTIVE = "ACTIVE", "Активен"
        BLOCKED = "BLOCKED", "Заблокирован"

    merchant_id = models.CharField(
        primary_key=True,
        max_length=5,
        validators=[RegexValidator(r"^m_[0-9]{3}$")],
    )
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="owned_merchant",
    )
    name = models.CharField(max_length=100)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.PENDING)
    description = models.CharField(max_length=200, blank=True)
    source_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Employee(models.Model):
    class Role(models.TextChoices):
        WAITER = "WAITER", "Официант"
        BARTENDER = "BARTENDER", "Бармен"
        HOSTESS = "HOSTESS", "Хостес"

    employee_id = models.CharField(
        primary_key=True,
        max_length=5,
        validators=[RegexValidator(r"^e_[0-9]{3}$")],
    )
    merchant = models.ForeignKey(Merchant, on_delete=models.PROTECT, related_name="employees")
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="employee_profile",
    )
    email = models.EmailField()
    phone = models.CharField(
        max_length=16,
        default="",
        blank=True,
        validators=[RegexValidator(r"^\+[1-9][0-9]{7,14}$", "Введите телефон в формате +79991234567.")],
    )
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.WAITER)
    payment_details = models.CharField(
        max_length=8,
        validators=[RegexValidator(r"^\*{4}[0-9]{4}$")],
    )
    invite_token_hash = models.CharField(max_length=64, blank=True)
    invite_expires_at = models.DateTimeField(null=True, blank=True)
    photo_png = models.BinaryField(null=True, blank=True)
    source_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["merchant", "email"], name="unique_employee_email_per_merchant"),
        ]

    def __str__(self):
        return self.name


class QRLink(models.Model):
    qr_id = models.CharField(
        primary_key=True,
        max_length=32,
        validators=[RegexValidator(r"^qr_[A-Za-z0-9_-]+$")],
    )
    merchant = models.ForeignKey(Merchant, on_delete=models.PROTECT, related_name="qr_links")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="qr_links")
    nonce = models.CharField(max_length=6, unique=True, validators=[RegexValidator(r"^[a-f0-9]{6}$")])
    expires_at = models.DateTimeField()
    signature = models.CharField(max_length=16, validators=[RegexValidator(r"^[a-f0-9]{16}$")])
    currency = models.CharField(max_length=3, default="RUB")
    used_at = models.DateTimeField(null=True, blank=True)
    source_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class TipGoal(models.Model):
    goal_id = models.CharField(primary_key=True, max_length=36)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="tip_goals")
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=300, blank=True)
    target_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=Q(target_amount__gt=0), name="tip_goal_target_positive"),
        ]

    @property
    def collected_amount(self):
        return self.payments.filter(status=Payment.Status.SUCCESS).aggregate(
            total=models.Sum("tip")
        )["total"] or Decimal("0.00")

    @property
    def progress_pct(self):
        return min(100, int(self.collected_amount * 100 / self.target_amount))


class ComplimentOption(models.Model):
    code = models.CharField(max_length=16, primary_key=True)
    label = models.CharField(max_length=64)

    def __str__(self):
        return self.label


class Payment(models.Model):
    class Status(models.TextChoices):
        CREATED = "CREATED", "Создан"
        PENDING = "PENDING", "В обработке"
        SUCCESS = "SUCCESS", "Успешен"
        DECLINED = "DECLINED", "Отклонен"
        CANCELED = "CANCELED", "Отменен"

    class Method(models.TextChoices):
        SBP = "SBP", "СБП"
        CARD = "CARD", "Банковская карта"
        SBERPAY = "SBERPAY", "SberPay"
        APPLE_PAY = "APPLE_PAY", "Apple Pay"

    class Compliment(models.TextChoices):
        FRIENDLY = "FRIENDLY", "Дружелюбие"
        ATTENTIVE = "ATTENTIVE", "Внимательность"
        FAST = "FAST", "Быстрое обслуживание"
        PROFESSIONAL = "PROFESSIONAL", "Профессионализм"
        HOSPITABLE = "HOSPITABLE", "Гостеприимство"

    payment_id = models.CharField(
        primary_key=True,
        max_length=12,
        validators=[RegexValidator(r"^p_[0-9]{4,8}$")],
    )
    merchant = models.ForeignKey(Merchant, on_delete=models.PROTECT, related_name="payments")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="payments")
    qr = models.ForeignKey(QRLink, on_delete=models.PROTECT, related_name="payments")
    tip = models.DecimalField(max_digits=10, decimal_places=2)
    service_fee = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    payment_method = models.CharField(max_length=10, choices=Method.choices, default=Method.SBP)
    goal = models.ForeignKey(TipGoal, null=True, blank=True, on_delete=models.SET_NULL, related_name="payments")
    service_rating = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    restaurant_rating = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)])
    restaurant_comment = models.CharField(max_length=500, blank=True)
    compliment = models.CharField(max_length=16, choices=Compliment.choices, blank=True)
    compliments = models.ManyToManyField(ComplimentOption, blank=True, related_name="payments")
    employee_comment = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.CREATED)
    idempotency_key = models.CharField(max_length=128)
    error_code = models.CharField(max_length=64, blank=True)
    source_metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["merchant", "idempotency_key"],
                name="unique_payment_idempotency_per_merchant",
            ),
            models.CheckConstraint(check=Q(tip__gt=0), name="payment_tip_positive"),
            models.CheckConstraint(check=Q(tip__lte=1000000), name="payment_tip_maximum"),
            models.CheckConstraint(
                check=Q(service_fee__in=[Decimal("0.00"), Decimal("25.00")]),
                name="payment_service_fee_valid",
            ),
            models.CheckConstraint(
                check=Q(service_rating__isnull=True) | Q(service_rating__gte=1, service_rating__lte=5),
                name="payment_service_rating_range",
            ),
            models.CheckConstraint(
                check=Q(restaurant_rating__isnull=True) | Q(restaurant_rating__gte=1, restaurant_rating__lte=5),
                name="payment_restaurant_rating_range",
            ),
        ]

    @property
    def amount_total(self):
        return self.tip + self.service_fee


class TipReport(models.Model):
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name="reports")
    start_date = models.DateField()
    end_date = models.DateField()
    tips_total = models.DecimalField(max_digits=12, decimal_places=2)
    payments_count = models.PositiveIntegerField()
    avg_tip_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    success_rate = models.DecimalField(max_digits=5, decimal_places=4)
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["merchant", "start_date", "end_date"],
                name="unique_report_period_per_merchant",
            ),
        ]


class AuditEvent(models.Model):
    class Actor(models.TextChoices):
        SYSTEM = "system", "Система"
        CLIENT = "client", "Клиент"
        OFFICER = "officer", "Официант"
        MERCHANT = "merchant", "Мерчант"
        ADMIN = "admin", "Администратор"

    event_id = models.CharField(primary_key=True, max_length=36)
    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="audit_events")
    qr = models.ForeignKey(QRLink, on_delete=models.PROTECT, related_name="audit_events")
    action = models.CharField(max_length=32)
    from_status = models.CharField(max_length=8, blank=True)
    to_status = models.CharField(max_length=8)
    amount_total = models.DecimalField(max_digits=11, decimal_places=2)
    actor = models.CharField(max_length=16, choices=Actor.choices)
    at = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict, blank=True)
