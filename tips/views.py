import hashlib
import hmac
import re
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps
from uuid import uuid4

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.db.models import Avg, Sum
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from .models import AuditEvent, Employee, Merchant, Payment, QRLink, TipGoal, TipReport, UserProfile
from .services import (
    DomainError,
    _id,
    _money,
    cancel_payment,
    confirm_payment,
    create_payment,
    create_qr,
    hash_invite_token,
    new_invite_token,
    parse_json_request,
    payment_data,
    serialize_qr,
    validate_qr,
)

User = get_user_model()


def json_endpoint(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        try:
            return view(request, *args, **kwargs)
        except DomainError as exc:
            return JsonResponse(
                {
                    "error_code": exc.error_code,
                    "message": exc.message,
                    "retryable": exc.retryable,
                    "details": exc.details,
                },
                status=exc.status,
            )
        except (KeyError, TypeError, ValueError):
            return JsonResponse(
                {
                    "error_code": "INVALID_REQUEST",
                    "message": "Отсутствует или некорректно задано обязательное поле",
                    "retryable": False,
                    "details": {},
                },
                status=422,
            )

    return wrapped


def authenticated(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error_code": "AUTH_REQUIRED", "message": "Требуется авторизация", "retryable": False, "details": {}},
                status=401,
            )
        return view(request, *args, **kwargs)

    return wrapped


def staff_member(request):
    employee = getattr(request.user, "employee_profile", None)
    if employee:
        return employee, employee.merchant
    merchant = getattr(request.user, "owned_merchant", None)
    if merchant:
        return None, merchant
    return None, None


@require_http_methods(["GET"])
@ensure_csrf_cookie
def health(request):
    return JsonResponse({"status": "ok", "csrfToken": get_token(request)})


@require_http_methods(["GET"])
@json_endpoint
def pay_page(request):
    qr_id = request.GET.get("qr")
    if not qr_id:
        raise DomainError("INVALID_QR", "Укажите идентификатор QR", 422)
    return _qr_info(qr_id)


@require_http_methods(["POST"])
@json_endpoint
def login_user(request):
    data = parse_json_request(request)
    email = str(data.get("email", "")).strip().lower()
    password = str(data.get("password", ""))
    user = authenticate(request, username=email, password=password)
    if user is None:
        raise DomainError("INVALID_CREDENTIALS", "Неверный email или пароль", 401)
    login(request, user)
    return JsonResponse({"status": "ok", "user_id": user.pk})


@require_http_methods(["POST"])
@json_endpoint
@authenticated
def logout_user(request):
    logout(request)
    return JsonResponse({"status": "ok"})


@require_http_methods(["POST"])
@json_endpoint
def register_merchant(request):
    data = parse_json_request(request)
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    phone = str(data.get("phone", "")).strip()
    password = str(data.get("password", ""))
    description = str(data.get("description", "")).strip()
    if not (1 <= len(name) <= 100) or not email or len(email) > 254 or len(description) > 200 or len(password) < 12:
        raise DomainError("INVALID_REGISTRATION", "Проверьте имя, email, телефон и пароль (не менее 12 символов)", 422)
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", phone):
        raise DomainError("INVALID_PHONE", "Введите телефон в международном формате, например +79991234567", 422)
    try:
        validate_email(email)
    except ValidationError:
        raise DomainError("INVALID_REGISTRATION", "Укажите корректный email", 422)
    if UserProfile.objects.filter(email__iexact=email).exists():
        raise DomainError("EMAIL_EXISTS", "Этот email уже зарегистрирован", 409)
    if User.objects.filter(username=email).exists():
        raise DomainError("ACCOUNT_EXISTS", "Аккаунт с таким email уже существует", 409)
    if UserProfile.objects.filter(phone=phone).exists():
        raise DomainError("PHONE_EXISTS", "Этот номер телефона уже зарегистрирован", 409)
    with transaction.atomic():
        user = User.objects.create_user(username=email, email=email, password=password)
        UserProfile.objects.create(user=user, email=email, phone=phone)
        merchant = Merchant.objects.create(
            merchant_id=_id("m", Merchant, "merchant_id", 3),
            owner=user,
            name=name,
            description=description,
            status=Merchant.Status.PENDING,
        )
    return JsonResponse(
        {"merchant_id": merchant.merchant_id, "status": merchant.status, "message": "Заявка отправлена администратору"},
        status=201,
    )


@require_http_methods(["POST"])
@json_endpoint
def accept_employee_invite(request, employee_id):
    data = parse_json_request(request)
    token = str(data.get("invite_token", ""))
    password = str(data.get("password", ""))
    employee = Employee.objects.filter(pk=employee_id).select_related("merchant").first()
    if employee is None or not employee.invite_token_hash:
        raise DomainError("INVITE_INVALID", "Приглашение недействительно", 404)
    if not employee.invite_expires_at or employee.invite_expires_at <= timezone.now():
        raise DomainError("INVITE_EXPIRED", "Приглашение истекло", 410, retryable=True)
    if not hmac.compare_digest(employee.invite_token_hash, hash_invite_token(token)):
        raise DomainError("INVITE_INVALID", "Приглашение недействительно", 403)
    if len(password) < 12:
        raise DomainError("INVALID_PASSWORD", "Пароль должен содержать не менее 12 символов", 422)
    if User.objects.filter(username=employee.email).exists():
        raise DomainError("ACCOUNT_EXISTS", "Учётная запись с таким email уже существует", 409)
    with transaction.atomic():
        user = User.objects.create_user(
            username=employee.email,
            email=employee.email,
            password=password,
        )
        UserProfile.objects.create(user=user, email=employee.email, phone=employee.phone)
        employee.user = user
        employee.invite_token_hash = ""
        employee.invite_expires_at = None
        employee.save(update_fields=["user", "invite_token_hash", "invite_expires_at"])
    return JsonResponse({"employee_id": employee.employee_id, "status": "ACTIVE"}, status=200)


@require_http_methods(["POST"])
@json_endpoint
@authenticated
def invite_employee(request):
    data = parse_json_request(request)
    _, merchant = staff_member(request)
    if merchant is None:
        raise DomainError("FORBIDDEN", "Только владелец мерчанта может приглашать сотрудников", 403)
    if merchant.status != Merchant.Status.ACTIVE:
        raise DomainError("MERCHANT_BLOCKED", "Мерчант не активен", 403)
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    phone = str(data.get("phone", "")).strip()
    last4 = str(data.get("payout_last4", ""))
    role = str(data.get("role", Employee.Role.WAITER))
    if (
        not name
        or len(name) > 100
        or "@" not in email
        or len(email) > 254
        or not re.fullmatch(r"\+[1-9][0-9]{7,14}", phone)
        or len(last4) != 4
        or not last4.isdigit()
        or role not in Employee.Role.values
    ):
        raise DomainError("INVALID_EMPLOYEE", "Проверьте имя, email, телефон, должность и последние 4 цифры реквизита", 422)
    try:
        validate_email(email)
    except ValidationError:
        raise DomainError("INVALID_EMPLOYEE", "Укажите корректный email", 422)
    if UserProfile.objects.filter(email__iexact=email).exists():
        raise DomainError("EMAIL_EXISTS", "Этот email уже зарегистрирован", 409)
    if Employee.objects.filter(merchant=merchant, email=email).exists() or User.objects.filter(username=email).exists():
        raise DomainError("ACCOUNT_EXISTS", "Сотрудник с таким email уже зарегистрирован", 409)
    if UserProfile.objects.filter(phone=phone).exists():
        raise DomainError("PHONE_EXISTS", "Этот номер телефона уже зарегистрирован", 409)
    token = new_invite_token()
    employee = Employee.objects.create(
        employee_id=_id("e", Employee, "employee_id", 3),
        merchant=merchant,
        email=email,
        phone=phone,
        name=name,
        role=role,
        payment_details="****" + last4,
        invite_token_hash=hash_invite_token(token),
        invite_expires_at=timezone.now() + timedelta(hours=72),
    )
    return JsonResponse(
        {
            "employee_id": employee.employee_id,
            "status": "INVITED",
            "invite_token": token,
            "payment_details": employee.payment_details,
            "role": employee.role,
        },
        status=201,
    )


@require_http_methods(["POST"])
@json_endpoint
@authenticated
def generate_qr(request):
    data = parse_json_request(request)
    employee, merchant = staff_member(request)
    if employee is None and merchant is None and request.user.is_staff:
        selected = Employee.objects.filter(pk=data.get("employee_id")).select_related("merchant").first()
        if selected is None:
            raise DomainError("EMPLOYEE_NOT_FOUND", "Сотрудник не найден", 404)
        merchant = selected.merchant
    elif employee is None and merchant is not None:
        employee_id = data.get("employee_id")
        if not employee_id:
            raise DomainError("EMPLOYEE_REQUIRED", "Укажите employee_id", 422)
        selected = Employee.objects.filter(pk=employee_id, merchant=merchant).first()
        if selected is None:
            raise DomainError("EMPLOYEE_NOT_FOUND", "Сотрудник не найден у этого мерчанта", 404)
    elif employee is not None:
        selected = employee
        employee_id = data.get("employee_id")
        if employee_id and employee_id != employee.employee_id:
            raise DomainError("FORBIDDEN", "Официант может создавать QR только для себя", 403)
    if merchant is None:
        raise DomainError("FORBIDDEN", "Недостаточно прав для генерации QR", 403)
    qr = create_qr(selected)
    return JsonResponse(serialize_qr(qr), status=201)


def _employee_for_request(request, employee_id=None):
    employee, merchant = staff_member(request)
    if employee:
        if employee_id and employee.employee_id != employee_id:
            raise DomainError("FORBIDDEN", "Доступ разрешён только к собственным данным", 403)
        return employee
    if merchant:
        if not employee_id:
            raise DomainError("EMPLOYEE_REQUIRED", "Укажите employee_id", 422)
        selected = Employee.objects.filter(pk=employee_id, merchant=merchant).first()
        if selected is None:
            raise DomainError("EMPLOYEE_NOT_FOUND", "Сотрудник не найден у этого мерчанта", 404)
        return selected
    if request.user.is_staff and employee_id:
        selected = Employee.objects.filter(pk=employee_id).first()
        if selected is None:
            raise DomainError("EMPLOYEE_NOT_FOUND", "Сотрудник не найден", 404)
        return selected
    raise DomainError("FORBIDDEN", "Недостаточно прав", 403)


@require_http_methods(["POST"])
@json_endpoint
@authenticated
def create_tip_goal(request):
    data = parse_json_request(request)
    employee = _employee_for_request(request, data.get("employee_id"))
    if employee.merchant.status != Merchant.Status.ACTIVE or employee.user_id is None:
        raise DomainError("EMPLOYEE_INACTIVE", "Цель доступна активным сотрудникам активного мерчанта", 409)
    title = str(data.get("title", "")).strip()
    description = str(data.get("description", "")).strip()
    target = _money(data.get("target_amount"), "GOAL_AMOUNT_INVALID")
    if not title or len(title) > 100 or len(description) > 300 or target <= 0 or target > Decimal("99999999.99"):
        raise DomainError("GOAL_INVALID", "Проверьте название, описание и целевую сумму сбора", 422)
    print(1)
    goal = TipGoal.objects.create(
        goal_id="g_{}".format(uuid4().hex),
        employee=employee,
        title=title,
        description=description,
        target_amount=target,
    )
    return JsonResponse(_goal_data(goal), status=201)


def _goal_data(goal):
    return {
        "goal_id": goal.goal_id,
        "employee_id": goal.employee_id,
        "title": goal.title,
        "description": goal.description,
        "target_amount": str(goal.target_amount),
        "collected_amount": str(goal.collected_amount),
        "progress_pct": goal.progress_pct,
        "is_active": goal.is_active,
    }


@require_http_methods(["GET"])
@json_endpoint
@authenticated
def employee_goals(request, employee_id):
    employee = _employee_for_request(request, employee_id)
    return JsonResponse(
        {"goals": [_goal_data(goal) for goal in employee.tip_goals.order_by("-created_at")]}
    )


@require_http_methods(["POST"])
@json_endpoint
@authenticated
def close_tip_goal(request, goal_id):
    _, merchant = staff_member(request)
    goal = TipGoal.objects.select_related("employee__merchant").filter(pk=goal_id).first()
    if goal is None:
        raise DomainError("GOAL_NOT_FOUND", "Цель сбора не найдена", 404)
    employee = getattr(request.user, "employee_profile", None)
    is_owner = merchant is not None and goal.employee.merchant_id == merchant.merchant_id
    is_staff = request.user.is_staff
    if not (is_owner or is_staff or (employee and employee.employee_id == goal.employee_id)):
        raise DomainError("FORBIDDEN", "Недостаточно прав для закрытия цели", 403)
    goal.is_active = False
    goal.save(update_fields=["is_active"])
    return JsonResponse(_goal_data(goal))


@require_http_methods(["GET"])
@json_endpoint
def get_qr(request, qr_id):
    return _qr_info(qr_id)


def _qr_info(qr_id):
    qr = QRLink.objects.select_related("merchant", "employee").filter(pk=qr_id).first()
    if qr is None:
        raise DomainError("INVALID_QR", "QR не найден", 404)
    validate_qr(qr)
    return JsonResponse(serialize_qr(qr))


@require_http_methods(["POST"])
@json_endpoint
def create_tip(request):
    data = parse_json_request(request)
    data["idempotency_key"] = request.headers.get(
        "Idempotency-Key",
        data.get("idempotency_key", ""),
    )
    payment, token, created = create_payment(
        qr_id=data["qr_id"],
        tip_amount=data["tip_amount"],
        payment_method=data["payment_method"],
        cover_service_fee=data.get("cover_service_fee", False),
        idempotency_key=data.get("idempotency_key", ""),
        goal_id=data.get("goal_id"),
        service_rating=data.get("service_rating"),
        restaurant_rating=data.get("restaurant_rating"),
        restaurant_comment=data.get("restaurant_comment", ""),
        compliment=data.get("compliment", ""),
        employee_comment=data.get("employee_comment", ""),
    )
    return JsonResponse(payment_data(payment, token), status=201 if created else 200)


@require_http_methods(["POST"])
@json_endpoint
def confirm_tip(request, payment_id):
    data = parse_json_request(request)
    payment = confirm_payment(payment_id, data.get("confirm_token", ""))
    return JsonResponse(
        payment_data(payment),
        status=402 if payment.status == Payment.Status.DECLINED else 200,
    )


@require_http_methods(["POST"])
@json_endpoint
def cancel_tip(request, payment_id):
    data = parse_json_request(request)
    payment = cancel_payment(payment_id, data.get("confirm_token", ""))
    return JsonResponse(payment_data(payment))


def _parse_report_dates(request):
    try:
        start = date.fromisoformat(request.GET["from"])
        end = date.fromisoformat(request.GET["to"])
    except (KeyError, ValueError):
        raise DomainError("INVALID_PERIOD", "Параметры from и to должны быть датами YYYY-MM-DD", 422)
    if end < start or (end - start).days > 366:
        raise DomainError("INVALID_PERIOD", "Период должен быть неотрицательным и не длиннее 367 дней", 422)
    return start, end


def _report_queryset(merchant, start, end):
    start_at = timezone.make_aware(datetime.combine(start, time.min))
    end_at = timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min))
    return Payment.objects.filter(merchant=merchant, created_at__gte=start_at, created_at__lt=end_at)


@require_http_methods(["GET"])
@json_endpoint
@authenticated
def tips_report(request):
    employee, owned_merchant = staff_member(request)
    merchant_id = request.GET.get("merchant_id")
    employee_id = request.GET.get("employee_id")
    start, end = _parse_report_dates(request)

    if employee_id:
        if employee is None or employee_id != employee.employee_id:
            raise DomainError("FORBIDDEN", "Официант может просматривать только свои чаевые", 403)
        payments = Payment.objects.filter(employee=employee, created_at__date__gte=start, created_at__date__lte=end)
        successful = payments.filter(status=Payment.Status.SUCCESS)
        total = successful.aggregate(value=Sum("tip"))["value"] or Decimal("0.00")
        count = payments.count()
        avg_amount = successful.aggregate(value=Avg("tip"))["value"] or Decimal("0.00")
        daily = (
            successful.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(tips=Sum("tip"))
            .order_by("-tips", "day")
            .first()
        )
        return JsonResponse(
            {
                "employee_id": employee.employee_id,
                "period": "{}-{}".format(start.isoformat(), end.isoformat()),
                "tips_total": str(total.quantize(Decimal("0.01"))),
                "payments_count": count,
                "avg_tip_amount": str(avg_amount.quantize(Decimal("0.01"))),
                "top_day": daily["day"].isoformat() if daily else None,
            }
        )
    if request.user.is_staff and merchant_id:
        merchant = Merchant.objects.filter(pk=merchant_id).first()
    elif owned_merchant and merchant_id == owned_merchant.merchant_id:
        merchant = owned_merchant
    else:
        merchant = None
    if merchant is None:
        raise DomainError("FORBIDDEN", "Отчёт доступен только владельцу мерчанта или администратору", 403)
    payments = _report_queryset(merchant, start, end)
    successful = payments.filter(status=Payment.Status.SUCCESS)
    aggregates = successful.aggregate(tips=Sum("tip"))
    tips_total = aggregates["tips"] or Decimal("0.00")
    payments_count = payments.count()
    successful_count = successful.count()
    avg_tip = tips_total / successful_count if successful_count else Decimal("0")
    success_rate = Decimal(successful_count) / payments_count if payments_count else Decimal("0")
    TipReport.objects.update_or_create(
        merchant=merchant,
        start_date=start,
        end_date=end,
        defaults={
            "tips_total": tips_total,
            "payments_count": payments_count,
            "avg_tip_amount": avg_tip.quantize(Decimal("0.01")),
            "success_rate": success_rate.quantize(Decimal("0.0001")),
        },
    )
    return JsonResponse(
        {
            "merchant_id": merchant.merchant_id,
            "period": "{}-{}".format(start.isoformat(), end.isoformat()),
            "tips_total": str(tips_total.quantize(Decimal("0.01"))),
            "payments_count": payments_count,
            "avg_tip_amount": str(avg_tip.quantize(Decimal("0.01"))),
            "success_rate": float(success_rate.quantize(Decimal("0.0001"))),
        }
    )


@require_http_methods(["GET"])
@json_endpoint
@authenticated
def daily_tips_report(request):
    _, owned_merchant = staff_member(request)
    merchant_id = request.GET.get("merchant_id")
    start, end = _parse_report_dates(request)
    if request.user.is_staff and merchant_id:
        merchant = Merchant.objects.filter(pk=merchant_id).first()
    elif owned_merchant and merchant_id == owned_merchant.merchant_id:
        merchant = owned_merchant
    else:
        merchant = None
    if merchant is None:
        raise DomainError("FORBIDDEN", "Отчёт доступен только владельцу мерчанта или администратору", 403)

    daily = defaultdict(lambda: {"tips": Decimal("0.00"), "count": 0})
    for payment in _report_queryset(merchant, start, end).filter(status=Payment.Status.SUCCESS).only(
        "created_at", "tip"
    ):
        day = timezone.localtime(payment.created_at).date().isoformat()
        daily[day]["tips"] += payment.tip
        daily[day]["count"] += 1

    rows = []
    for day, values in sorted(daily.items()):
        avg_tip = values["tips"] / values["count"]
        rows.append(
            {
                "date": day,
                "tips_total": str(values["tips"].quantize(Decimal("0.01"))),
                "payments_count": values["count"],
                "avg_tip_amount": str(avg_tip.quantize(Decimal("0.01"))),
            }
        )
    return JsonResponse({"merchant_id": merchant.merchant_id, "daily": rows})
