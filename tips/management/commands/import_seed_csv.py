import csv
import re
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from tips.models import AuditEvent, Employee, Merchant, Payment, QRLink
from tips.services import sign_qr


FILES = {
    "merchants": ("merchants.csv", {"merchant_id", "name", "status", "description"}),
    "employees": ("employees.csv", {"employee_id", "merchant_id", "name", "payment_details"}),
    "qr_links": (
        "qr_links.csv",
        {"qr_id", "merchant_id", "employee_id", "receipt_id", "nonce", "exp", "signature"},
    ),
    "payments": (
        "payments.csv",
        {"payment_id", "merchant_id", "employee_id", "amount", "tip", "status", "timestamp"},
    ),
}


def _fail(filename, line, message):
    raise CommandError("{}:{}: {}".format(filename, line, message))


def _read_csv(data_dir, name):
    filename, required_columns = FILES[name]
    path = data_dir / filename
    try:
        with path.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if not reader.fieldnames or not required_columns.issubset(reader.fieldnames):
                missing = sorted(required_columns - set(reader.fieldnames or ()))
                raise CommandError("{}: missing columns: {}".format(filename, ", ".join(missing)))
            rows = []
            for line, row in enumerate(reader, start=2):
                if None in row or any(value is None for value in row.values()):
                    _fail(filename, line, "row has an unexpected number of columns")
                if not any(value.strip() for value in row.values()):
                    continue
                rows.append((line, {key: value.strip() for key, value in row.items()}))
            return rows
    except OSError as exc:
        raise CommandError("Cannot read {}: {}".format(path, exc)) from exc
    except csv.Error as exc:
        raise CommandError("Invalid CSV {}: {}".format(path, exc)) from exc


def _decimal(value, filename, line, field, *, positive=False):
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        _fail(filename, line, "{} must be a decimal number".format(field))
    if not amount.is_finite() or (positive and amount <= 0):
        _fail(filename, line, "{} must be a positive finite amount".format(field))
    return amount


def _datetime(value, filename, line, field):
    parsed = parse_datetime(value)
    if parsed is None or timezone.is_naive(parsed):
        _fail(filename, line, "{} must be an ISO-8601 datetime with timezone".format(field))
    return parsed


def _matching_qr_id(payment_id, qr_ids):
    payment_number = int(payment_id.split("_", 1)[1])
    matches = [
        qr_id
        for qr_id in qr_ids
        if re.fullmatch(r"qr_[0-9]+", qr_id)
        and int(qr_id.split("_", 1)[1]) == payment_number
    ]
    return matches[0] if len(matches) == 1 else None


class Command(BaseCommand):
    help = "Import seed CSV data without updating existing database rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            default=str(Path(settings.BASE_DIR) / "tasks" / "data"),
            help="Directory containing merchants.csv, employees.csv, qr_links.csv and payments.csv.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and show the import plan, then roll back all writes.",
        )

    def handle(self, *args, **options):
        data_dir = Path(options["data_dir"])
        if not settings.TIP_QR_SECRET:
            raise CommandError("TIP_QR_SECRET must be configured before importing QR links.")

        dataset = {name: _read_csv(data_dir, name) for name in FILES}
        self._validate(dataset)
        counts = {
            name: {"created": 0, "skipped": 0}
            for name in ("merchants", "employees", "qr_links", "payments")
        }

        try:
            with transaction.atomic():
                self._import_merchants(dataset["merchants"], counts["merchants"])
                self._import_employees(dataset["employees"], counts["employees"])
                self._import_qrs(dataset, counts["qr_links"])
                self._import_payments(dataset, counts["payments"])
                if options["dry_run"]:
                    transaction.set_rollback(True)
        except IntegrityError as exc:
            raise CommandError(
                "Import failed due to a database constraint; no import changes were committed: {}".format(exc)
            ) from exc

        prefix = "Would " if options["dry_run"] else ""
        for name, result in counts.items():
            self.stdout.write(
                "{}{}: {} created, {} skipped".format(
                    prefix, name, result["created"], result["skipped"]
                )
            )
        if options["dry_run"]:
            self.stdout.write("Dry run complete; all database writes were rolled back.")

    def _validate(self, dataset):
        merchants = {}
        employees = {}
        qrs = {}
        nonces = set()
        payments = {}

        for line, row in dataset["merchants"]:
            merchant_id = row["merchant_id"]
            if not re.fullmatch(r"m_[0-9]{3}", merchant_id):
                _fail("merchants.csv", line, "invalid merchant_id")
            if merchant_id in merchants:
                _fail("merchants.csv", line, "duplicate merchant_id {}".format(merchant_id))
            if not row["name"] or len(row["name"]) > 100 or len(row["description"]) > 200:
                _fail("merchants.csv", line, "name/description exceeds model limits")
            if row["status"] not in Merchant.Status.values:
                _fail("merchants.csv", line, "invalid merchant status")
            merchants[merchant_id] = row

        for line, row in dataset["employees"]:
            employee_id = row["employee_id"]
            merchant_id = row["merchant_id"]
            if not re.fullmatch(r"e_[0-9]{3}", employee_id):
                _fail("employees.csv", line, "invalid employee_id")
            if employee_id in employees:
                _fail("employees.csv", line, "duplicate employee_id {}".format(employee_id))
            if merchant_id not in merchants and not Merchant.objects.filter(pk=merchant_id).exists():
                _fail("employees.csv", line, "unknown merchant_id {}".format(merchant_id))
            if not row["name"] or len(row["name"]) > 100:
                _fail("employees.csv", line, "name must contain 1 to 100 characters")
            if not re.fullmatch(r"\*{4}[0-9]{4}", row["payment_details"]):
                _fail("employees.csv", line, "payment_details must be masked as ****NNNN")
            existing = Employee.objects.filter(pk=employee_id).first()
            if existing and existing.merchant_id != merchant_id:
                _fail("employees.csv", line, "existing employee belongs to a different merchant")
            employees[employee_id] = row

        for line, row in dataset["qr_links"]:
            qr_id = row["qr_id"]
            merchant_id = row["merchant_id"]
            employee_id = row["employee_id"]
            if not re.fullmatch(r"qr_[A-Za-z0-9_-]+", qr_id):
                _fail("qr_links.csv", line, "invalid qr_id")
            if qr_id in qrs:
                _fail("qr_links.csv", line, "duplicate qr_id {}".format(qr_id))
            employee = employees.get(employee_id)
            employee_merchant_id = employee["merchant_id"] if employee else (
                Employee.objects.filter(pk=employee_id).values_list("merchant_id", flat=True).first()
            )
            if employee_merchant_id is None:
                _fail("qr_links.csv", line, "unknown employee_id {}".format(employee_id))
            if employee_merchant_id != merchant_id:
                _fail("qr_links.csv", line, "QR merchant does not match employee merchant")
            if merchant_id not in merchants and not Merchant.objects.filter(pk=merchant_id).exists():
                _fail("qr_links.csv", line, "unknown merchant_id {}".format(merchant_id))
            if not re.fullmatch(r"[a-fA-F0-9]{6}", row["nonce"]):
                _fail("qr_links.csv", line, "nonce must contain 6 hexadecimal characters")
            nonce = row["nonce"].lower()
            if nonce in nonces:
                _fail("qr_links.csv", line, "duplicate nonce {}".format(row["nonce"]))
            nonces.add(nonce)
            if not re.fullmatch(r"[a-fA-F0-9]{16}", row["signature"]):
                _fail("qr_links.csv", line, "signature must contain 16 hexadecimal characters")
            _datetime(row["exp"], "qr_links.csv", line, "exp")
            existing = QRLink.objects.filter(pk=qr_id).first()
            if existing and (
                existing.merchant_id != merchant_id or existing.employee_id != employee_id
            ):
                _fail("qr_links.csv", line, "existing QR belongs to different merchant/employee")
            nonce_owner = QRLink.objects.filter(nonce=row["nonce"]).exclude(pk=qr_id).first()
            if nonce_owner:
                _fail("qr_links.csv", line, "nonce is already used by another QR")
            qrs[qr_id] = row

        for line, row in dataset["payments"]:
            payment_id = row["payment_id"]
            if not re.fullmatch(r"p_[0-9]{4,8}", payment_id):
                _fail("payments.csv", line, "invalid payment_id")
            if payment_id in payments:
                _fail("payments.csv", line, "duplicate payment_id {}".format(payment_id))
            employee_id = row["employee_id"]
            merchant_id = row["merchant_id"]
            employee = employees.get(employee_id)
            employee_merchant_id = employee["merchant_id"] if employee else (
                Employee.objects.filter(pk=employee_id).values_list("merchant_id", flat=True).first()
            )
            if employee_merchant_id is None or employee_merchant_id != merchant_id:
                _fail("payments.csv", line, "unknown employee or employee belongs to another merchant")
            if merchant_id not in merchants and not Merchant.objects.filter(pk=merchant_id).exists():
                _fail("payments.csv", line, "unknown merchant_id {}".format(merchant_id))
            qr_id = _matching_qr_id(
                payment_id,
                set(qrs) | set(QRLink.objects.values_list("pk", flat=True)),
            )
            if qr_id is None:
                _fail("payments.csv", line, "missing or ambiguous matching QR for {}".format(payment_id))
            qr = qrs.get(qr_id)
            if qr is None:
                qr = QRLink.objects.filter(pk=qr_id).values("merchant_id", "employee_id").first()
            if qr is None:
                _fail("payments.csv", line, "missing matching QR {}".format(qr_id))
            if qr["merchant_id"] != merchant_id or qr["employee_id"] != employee_id:
                _fail("payments.csv", line, "payment merchant/employee does not match QR")
            tip = _decimal(row["tip"], "payments.csv", line, "tip", positive=True)
            if tip > Decimal("1000000") or tip.quantize(Decimal("0.01")) != tip:
                _fail("payments.csv", line, "tip must be at most 1,000,000 with two decimal places")
            _decimal(row["amount"], "payments.csv", line, "amount", positive=True)
            if row["status"] not in Payment.Status.values:
                _fail("payments.csv", line, "invalid payment status")
            _datetime(row["timestamp"], "payments.csv", line, "timestamp")
            payments[payment_id] = row

    def _import_merchants(self, rows, result):
        for _, row in rows:
            _, created = Merchant.objects.get_or_create(
                pk=row["merchant_id"],
                defaults={
                    "name": row["name"],
                    "status": row["status"],
                    "description": row["description"],
                    "source_metadata": {"csv": "merchants.csv", "row": row},
                },
            )
            result["created" if created else "skipped"] += 1

    def _import_employees(self, rows, result):
        for _, row in rows:
            _, created = Employee.objects.get_or_create(
                pk=row["employee_id"],
                defaults={
                    "merchant_id": row["merchant_id"],
                    "name": row["name"],
                    "email": "{}@import.invalid".format(row["employee_id"]),
                    "payment_details": row["payment_details"],
                    "source_metadata": {"csv": "employees.csv", "row": row},
                },
            )
            result["created" if created else "skipped"] += 1

    def _import_qrs(self, dataset, result):
        payment_by_qr = {
            _matching_qr_id(
                row["payment_id"],
                [qr_row["qr_id"] for _, qr_row in dataset["qr_links"]],
            ): row
            for _, row in dataset["payments"]
        }
        for _, row in dataset["qr_links"]:
            expires_at = _datetime(row["exp"], "qr_links.csv", 0, "exp")
            signature = sign_qr(
                row["merchant_id"],
                row["employee_id"],
                row["nonce"].lower(),
                expires_at,
            )
            payment = payment_by_qr.get(row["qr_id"])
            used_at = (
                _datetime(payment["timestamp"], "payments.csv", 0, "timestamp")
                if payment
                else None
            )
            _, created = QRLink.objects.get_or_create(
                pk=row["qr_id"],
                defaults={
                    "merchant_id": row["merchant_id"],
                    "employee_id": row["employee_id"],
                    "nonce": row["nonce"].lower(),
                    "expires_at": expires_at,
                    "signature": signature,
                    "used_at": used_at,
                    "source_metadata": {"csv": "qr_links.csv", "row": row},
                },
            )
            result["created" if created else "skipped"] += 1
            if created:
                QRLink.objects.filter(pk=row["qr_id"]).update(
                    created_at=expires_at - timedelta(hours=24)
                )

    def _import_payments(self, dataset, result):
        for _, row in dataset["payments"]:
            qr_id = _matching_qr_id(
                row["payment_id"],
                set(QRLink.objects.values_list("pk", flat=True)),
            )
            timestamp = _datetime(row["timestamp"], "payments.csv", 0, "timestamp")
            payment, created = Payment.objects.get_or_create(
                pk=row["payment_id"],
                defaults={
                    "merchant_id": row["merchant_id"],
                    "employee_id": row["employee_id"],
                    "qr_id": qr_id,
                    "tip": Decimal(row["tip"]),
                    "status": row["status"],
                    "idempotency_key": "csv-import:{}".format(row["payment_id"]),
                    "source_metadata": {"csv": "payments.csv", "row": row},
                },
            )
            result["created" if created else "skipped"] += 1
            if created:
                Payment.objects.filter(pk=payment.pk).update(
                    created_at=timestamp,
                    updated_at=timestamp,
                )
                event = AuditEvent.objects.create(
                    event_id="evt_import_{}".format(payment.pk),
                    payment=payment,
                    qr_id=qr_id,
                    action="payment_imported",
                    to_status=payment.status,
                    amount_total=payment.amount_total,
                    actor=AuditEvent.Actor.ADMIN,
                    at=timestamp,
                    details={"source": "payments.csv"},
                )
                AuditEvent.objects.filter(pk=event.pk).update(at=timestamp)
