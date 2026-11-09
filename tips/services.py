import base64
import hashlib
import hmac
import io
import json
import secrets
import xml.etree.ElementTree as ET
from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4

import qrcode
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone
from PIL import Image, ImageDraw
from qrcode.image.svg import SvgPathImage

from .models import AuditEvent, ComplimentOption, Employee, Merchant, Payment, QRLink, TipGoal

CENT = Decimal("0.01")
QR_IMAGE_SIZE = 196
QR_COLOR = "#2E1E14"
SVG_NAMESPACE = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NAMESPACE)


class DomainError(Exception):
    def __init__(self, error_code, message, status, retryable=False, details=None):
        self.error_code = error_code
        self.message = message
        self.status = status
        self.retryable = retryable
        self.details = details or {}


def _secret():
    secret = settings.TIP_QR_SECRET
    if not secret:
        raise ImproperlyConfigured("TIP_QR_SECRET must be configured before generating or verifying QR links")
    return secret.encode("utf-8")


def _id(prefix, model, field_name, width):
    last_value = model.objects.aggregate(last=Max(field_name))["last"]
    try:
        next_number = int(last_value.split("_")[-1]) + 1 if last_value else 1
    except ValueError:
        next_number = model.objects.count() + 1
    return "{}_{:0{}d}".format(prefix, next_number, width)


def _qr_payload(merchant_id, employee_id, nonce, expires_at):
    exp = expires_at.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return "{}|{}|{}|{}".format(merchant_id, employee_id, nonce, exp)


def sign_qr(merchant_id, employee_id, nonce, expires_at):
    digest = hmac.new(
        _secret(),
        _qr_payload(merchant_id, employee_id, nonce, expires_at).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest[:16]


def verify_qr_signature(qr):
    expected = sign_qr(qr.merchant_id, qr.employee_id, qr.nonce, qr.expires_at)
    return hmac.compare_digest(expected, qr.signature)


def _confirm_token(payment):
    message = "confirm|{}|{}|{}".format(payment.merchant_id, payment.payment_id, payment.idempotency_key)
    return hmac.new(_secret(), message.encode("utf-8"), hashlib.sha256).hexdigest()


def _audit(payment, action, old_status, new_status, actor, details=None):
    AuditEvent.objects.create(
        event_id="evt_{}".format(uuid4().hex),
        payment=payment,
        qr=payment.qr,
        action=action,
        from_status=old_status or "",
        to_status=new_status,
        amount_total=payment.amount_total,
        actor=actor,
        details=details or {},
    )


def validate_qr(qr):
    if not verify_qr_signature(qr):
        raise DomainError("INVALID_QR", "QR-подпись недействительна", 422)
    if qr.expires_at <= timezone.now():
        raise DomainError("QR_EXPIRED", "Срок действия QR истёк", 410, retryable=True)
    if qr.merchant.status != Merchant.Status.ACTIVE:
        raise DomainError("MERCHANT_BLOCKED", "Мерчант заблокирован", 403)
    if qr.used_at is not None:
        raise DomainError("QR_USED", "QR уже использован", 409)


def make_qr_image(payment_url):
    qr = _qr_code(payment_url)
    image = qr.make_image(
        image_factory=SvgPathImage,
        fill_color=QR_COLOR,
        back_color="#FFFFFF",
    )
    svg = ET.fromstring(image.to_string(encoding="unicode"))
    svg.set("width", "{}px".format(QR_IMAGE_SIZE))
    svg.set("height", "{}px".format(QR_IMAGE_SIZE))
    svg.set("fill", QR_COLOR)
    svg.attrib.pop("fill_color", None)
    svg.attrib.pop("back_color", None)
    for path in svg.findall("{{{}}}path".format(SVG_NAMESPACE)):
        path.set("fill", QR_COLOR)

    view_x, view_y, view_width, view_height = map(float, svg.get("viewBox").split())
    icon_size = min(view_width, view_height) * 0.18
    panel_size = icon_size * 1.15
    center_x = view_x + view_width / 2
    center_y = view_y + view_height / 2
    background = ET.Element(
        "{{{}}}rect".format(SVG_NAMESPACE),
        {
            "x": str(view_x),
            "y": str(view_y),
            "width": str(view_width),
            "height": str(view_height),
            "fill": "#FFFFFF",
        },
    )
    panel = ET.Element(
        "{{{}}}rect".format(SVG_NAMESPACE),
        {
            "x": str(center_x - panel_size / 2),
            "y": str(center_y - panel_size / 2),
            "width": str(panel_size),
            "height": str(panel_size),
            "rx": str(panel_size * 0.12),
            "fill": "#FFFFFF",
        },
    )
    svg.insert(0, panel)
    svg.insert(0, background)

    icon_source = ET.parse(settings.BASE_DIR / "Background+Border.svg").getroot()
    icon = ET.Element(
        "{{{}}}svg".format(SVG_NAMESPACE),
        dict(icon_source.attrib),
    )
    icon.set("x", str(center_x - icon_size / 2))
    icon.set("y", str(center_y - icon_size / 2))
    icon.set("width", str(icon_size))
    icon.set("height", str(icon_size))
    icon.set("preserveAspectRatio", "xMidYMid meet")
    icon.extend(list(icon_source))
    svg.append(icon)
    rendered = ET.tostring(svg, encoding="unicode")
    return base64.b64encode(rendered.encode("utf-8")).decode("ascii")


def _qr_code(payment_url):
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=1,
        border=4,
    )
    qr.add_data(payment_url)
    qr.make(fit=True)
    return qr


def make_qr_png(payment_url):
    image = _qr_code(payment_url).make_image(fill_color=QR_COLOR, back_color="#FFFFFF").convert("RGBA")
    image = image.resize((QR_IMAGE_SIZE, QR_IMAGE_SIZE), Image.Resampling.NEAREST)
    center = QR_IMAGE_SIZE // 2
    icon_size = round(QR_IMAGE_SIZE * 0.18)
    panel_size = round(icon_size * 1.15)
    panel_start = center - panel_size // 2
    icon_start = center - icon_size // 2
    ImageDraw.Draw(image).rounded_rectangle(
        (panel_start, panel_start, panel_start + panel_size, panel_start + panel_size),
        radius=round(panel_size * 0.12),
        fill="#FFFFFF",
    )
    icon = Image.open(settings.BASE_DIR / "Background+Border.png").convert("RGBA")
    icon = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
    image.alpha_composite(icon, (icon_start, icon_start))
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


@transaction.atomic
def create_qr(employee):
    merchant = employee.merchant
    if merchant.status != Merchant.Status.ACTIVE:
        raise DomainError("MERCHANT_BLOCKED", "Мерчант не активен", 403)
    if employee.user_id is None:
        raise DomainError("EMPLOYEE_INACTIVE", "Сотрудник ещё не принял приглашение", 409)
    expires_at = timezone.now() + timedelta(hours=settings.QR_TTL_HOURS)
    nonce = secrets.token_hex(3)

    qr = QRLink(
        qr_id=_id("qr", QRLink, "qr_id", 3),
        merchant=merchant,
        employee=employee,
        nonce=nonce,
        expires_at=expires_at,
        signature="0" * 16,
    )
    qr.signature = sign_qr(merchant.merchant_id, employee.employee_id, nonce, expires_at)
    try:
        qr.save()
    except IntegrityError:
        raise DomainError("QR_GENERATION_FAILED", "Не удалось создать QR; попробуйте ещё раз", 409, retryable=True)
    return qr


def serialize_qr(qr):
    payment_url = "{}/tip/{}".format("merci-chi.vercel.app", qr.qr_id)
    return {
        "qr_id": qr.qr_id,
        "merchant_id": qr.merchant_id,
        "merchant_name": qr.merchant.name,
        "employee_id": qr.employee_id,
        "employee_name": qr.employee.name,
        "employee_role": qr.employee.role,
        "employee_role_label": qr.employee.get_role_display(),
        "currency": qr.currency,
        # "tip_options": settings.TIP_OPTIONS,
        # "compliment_options": [{"value": value, "label": label} for value, label in Payment.Compliment.choices],
        # "payment_methods": [{"value": value, "label": label} for value, label in Payment.Method.choices],
        # "service_fee_amount": settings.SERVICE_FEE_AMOUNT,
        "active_goals": [
            {
                "goal_id": goal.goal_id,
                "employee_id": goal.employee_id,
                "title": goal.title,
                "description": goal.description,
                "target_amount": str(goal.target_amount),
                "collected_amount": str(goal.collected_amount),
                "progress_pct": goal.progress_pct,
                "is_active": goal.is_active,
            }
            for goal in qr.employee.tip_goals.filter(is_active=True).order_by("-created_at")
        ],
        "payment_url": payment_url,
        "employee_photo_url": "{}/api/v1/qr/{}/employee-photo".format(
            settings.PUBLIC_BASE_URL,
            qr.qr_id,
        ),
        "compliment_options": [
            {"value": value, "label": label}
            for value, label in Payment.Compliment.choices
        ],
        # "qr_image_url": "{}/api/v1/qr/{}/image".format(settings.PUBLIC_BASE_URL, qr.qr_id),
        # "qr_image_svg_base64": make_qr_image(payment_url),
        "exp": qr.expires_at.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }


def make_employee_placeholder_png():
    image = Image.new("RGB", (256, 256), "#F5EEE7")
    draw = ImageDraw.Draw(image)
    draw.ellipse((84, 40, 172, 128), fill="#B9A18D")
    draw.ellipse((54, 132, 202, 278), fill="#B9A18D")
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def _money(value, code):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite():
            raise DomainError(code, "Некорректная сумма", 422)
        result = amount.quantize(CENT, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise DomainError(code, "Сумма должна быть числом с точностью до копеек", 422)
    if result != amount:
        raise DomainError(code, "Сумма должна содержать не более двух знаков после запятой", 422)
    return result


@transaction.atomic
def create_payment(
    qr_id,
    tip_amount,
    payment_method,
    cover_service_fee,
    idempotency_key,
    goal_id=None,
    service_rating=None,
    restaurant_rating=None,
    restaurant_comment="",
    compliment="",
    compliments=None,
    employee_comment="",
):
    if not idempotency_key or len(idempotency_key) < 16 or len(idempotency_key) > 128:
        raise DomainError("IDEMPOTENCY_KEY_REQUIRED", "Ключ должен содержать от 16 до 128 символов", 422)
    qr = QRLink.objects.select_for_update().select_related("merchant", "employee").filter(pk=qr_id).first()
    if qr is None:
        raise DomainError("INVALID_QR", "QR не найден", 404)

    if payment_method not in Payment.Method.values:
        raise DomainError("PAYMENT_METHOD_INVALID", "Выберите доступный способ оплаты", 422)
    if not isinstance(cover_service_fee, bool):
        raise DomainError("INVALID_REQUEST", "cover_service_fee должен быть true или false", 422)
    tip = _money(tip_amount, "TIP_OUT_OF_RANGE")
    if tip <= 0 or tip > Decimal("1000000"):
        raise DomainError("TIP_OUT_OF_RANGE", "Чаевые должны быть от 0.01 до 1 000 000 рублей", 422)
    fee = Decimal("25.00") if cover_service_fee else Decimal("0.00")
    goal = None
    if goal_id:
        goal = TipGoal.objects.filter(
            pk=goal_id,
            employee=qr.employee,
        ).first()
        if goal is None:
            raise DomainError("GOAL_NOT_FOUND", "Цель сбора не найдена", 422)
    for field_name, rating in (
        ("оценка сервиса", service_rating),
        ("оценка ресторана", restaurant_rating),
    ):
        if rating is not None and (isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5):
            raise DomainError("RATING_OUT_OF_RANGE", "{} должна быть от 1 до 5".format(field_name), 422)
    if not isinstance(restaurant_comment, str) or not isinstance(employee_comment, str):
        raise DomainError("INVALID_REQUEST", "Комментарии должны быть текстом", 422)
    restaurant_comment = restaurant_comment.strip()
    employee_comment = employee_comment.strip()
    if len(restaurant_comment) > 500 or len(employee_comment) > 500:
        raise DomainError("COMMENT_TOO_LONG", "Комментарий не должен превышать 500 символов", 422)
    if compliments is None:
        compliments = []
    elif not isinstance(compliments, list):
        raise DomainError("COMPLIMENT_INVALID", "Комплименты должны быть переданы списком", 422)
    if compliment:
        if compliments:
            raise DomainError("COMPLIMENT_INVALID", "Передайте compliment или compliments, но не оба поля", 422)
        compliments = [compliment]
    if (
        len(compliments) > len(Payment.Compliment.choices)
        or len(compliments) != len(set(compliments))
        or any(value not in Payment.Compliment.values for value in compliments)
    ):
        raise DomainError("COMPLIMENT_INVALID", "Выберите комплименты из предложенных вариантов", 422)

    existing = Payment.objects.filter(merchant=qr.merchant, idempotency_key=idempotency_key).first()
    if existing:
        if (
            existing.qr_id != qr_id
            or existing.tip != tip
            or existing.payment_method != payment_method
            or existing.service_fee != fee
            or existing.goal_id != (goal.pk if goal else None)
            or existing.service_rating != service_rating
            or existing.restaurant_rating != restaurant_rating
            or existing.restaurant_comment != restaurant_comment
            or set(existing.compliments.values_list("code", flat=True)) != set(compliments)
            or existing.employee_comment != employee_comment
        ):
            raise DomainError("IDEMPOTENCY_CONFLICT", "Ключ уже использован для другого запроса", 409)
        return existing, _confirm_token(existing), False

    if goal is not None and not goal.is_active:
        raise DomainError("GOAL_NOT_FOUND", "Цель сбора уже закрыта", 422)
    validate_qr(qr)

    payment = Payment(
        payment_id=_id("p", Payment, "payment_id", 4),
        merchant=qr.merchant,
        employee=qr.employee,
        qr=qr,
        tip=tip,
        service_fee=fee,
        payment_method=payment_method,
        goal=goal,
        service_rating=service_rating,
        restaurant_rating=restaurant_rating,
        restaurant_comment=restaurant_comment,
        compliment=compliments[0] if len(compliments) == 1 else "",
        employee_comment=employee_comment,
        idempotency_key=idempotency_key,
        status=Payment.Status.CREATED,
    )
    payment.save()
    if compliments:
        payment.compliments.set(ComplimentOption.objects.filter(code__in=compliments))
    qr.used_at = timezone.now()
    qr.save(update_fields=["used_at"])
    _audit(payment, "payment_created", "", Payment.Status.CREATED, AuditEvent.Actor.CLIENT)
    return payment, _confirm_token(payment), True


def payment_data(payment, confirm_token=None):
    return {
        "payment_id": payment.payment_id,
        "status": payment.status,
        "amount_total": str(payment.amount_total.quantize(CENT)),
        "tip_amount": str(payment.tip.quantize(CENT)),
        "service_fee_amount": str(payment.service_fee.quantize(CENT)),
        "payment_method": payment.payment_method,
        "goal_id": payment.goal_id,
        "compliments": list(payment.compliments.values_list("code", flat=True)),
        "confirm_token": confirm_token,
        "error_code": payment.error_code or None,
    }


def _gateway_result(qr_id, nonce):
    value = int(hashlib.sha256((qr_id + nonce).encode("utf-8")).hexdigest(), 16) % 10
    if value <= 7:
        return "SUCCESS", ""
    if value == 8:
        return "DECLINED", "CARD_DECLINED"
    return "PENDING", "GATEWAY_TIMEOUT"


@transaction.atomic
def confirm_payment(payment_id, token):
    payment = Payment.objects.select_for_update().select_related("qr").filter(pk=payment_id).first()
    if payment is None:
        raise DomainError("PAYMENT_NOT_FOUND", "Платёж не найден", 404)
    if not token or not hmac.compare_digest(_confirm_token(payment), token):
        raise DomainError("INVALID_CONFIRM_TOKEN", "Токен подтверждения недействителен", 403)
    if payment.status not in (Payment.Status.CREATED, Payment.Status.PENDING):
        raise DomainError("PAYMENT_STATE_CONFLICT", "Платёж уже завершён", 409)

    old_status = payment.status
    if old_status == Payment.Status.CREATED:
        payment.status = Payment.Status.PENDING
        payment.save(update_fields=["status", "updated_at"])
        _audit(payment, "payment_submitted", old_status, Payment.Status.PENDING, AuditEvent.Actor.CLIENT)

    status, error_code = _gateway_result(payment.qr_id, payment.qr.nonce)
    if status == Payment.Status.PENDING:
        payment.error_code = error_code
        payment.save(update_fields=["error_code", "updated_at"])
        _audit(
            payment,
            "payment_timeout",
            Payment.Status.PENDING,
            Payment.Status.PENDING,
            AuditEvent.Actor.SYSTEM,
            details={"error_code": error_code},
        )
        return payment

    old_status = payment.status
    payment.status = status
    payment.error_code = error_code
    payment.save(update_fields=["status", "error_code", "updated_at"])
    action = "payment_confirmed" if status == Payment.Status.SUCCESS else "payment_declined"
    _audit(payment, action, old_status, status, AuditEvent.Actor.SYSTEM)
    return payment


@transaction.atomic
def cancel_payment(payment_id, token):
    payment = Payment.objects.select_for_update().filter(pk=payment_id).first()
    if payment is None:
        raise DomainError("PAYMENT_NOT_FOUND", "Платёж не найден", 404)
    if not token or not hmac.compare_digest(_confirm_token(payment), token):
        raise DomainError("INVALID_CONFIRM_TOKEN", "Токен подтверждения недействителен", 403)
    if payment.status != Payment.Status.CREATED:
        raise DomainError("CANCEL_NOT_ALLOWED", "Отменить можно только платёж до подтверждения", 409)
    old_status = payment.status
    payment.status = Payment.Status.CANCELED
    payment.save(update_fields=["status", "updated_at"])
    _audit(payment, "payment_canceled", old_status, payment.status, AuditEvent.Actor.CLIENT)
    return payment


def parse_json_request(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise DomainError("INVALID_JSON", "Тело запроса должно быть корректным JSON", 400)
    if not isinstance(data, dict):
        raise DomainError("INVALID_JSON", "Ожидается JSON-объект", 400)
    return data


def new_invite_token():
    return secrets.token_urlsafe(32)


def hash_invite_token(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
