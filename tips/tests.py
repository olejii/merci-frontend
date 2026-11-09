import base64
import hashlib
import io
import tempfile
import xml.etree.ElementTree as ET
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image

from .models import Employee, Merchant, Payment, QRLink, TipGoal, UserProfile
from .services import sign_qr, verify_qr_signature

User = get_user_model()


@override_settings(TIP_QR_SECRET="test-secret", PUBLIC_BASE_URL="http://testserver")
class TipsApiTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user(username="owner@example.com", password="valid-password-123")
        UserProfile.objects.create(
            user=owner,
            email="owner@example.com",
            phone="+79990000001",
        )
        self.merchant = Merchant.objects.create(
            merchant_id="m_001",
            owner=owner,
            name="Вкус-Сервис",
            status=Merchant.Status.ACTIVE,
        )
        self.employee = Employee.objects.create(
            employee_id="e_001",
            merchant=self.merchant,
            user=User.objects.create_user(username="officer@example.com", password="valid-password-456"),
            email="officer@example.com",
            phone="+79990000002",
            name="Анна",
            payment_details="****1234",
        )
        self.client.force_login(owner)

    def make_qr(self, qr_id="qr_001", nonce="000001", hours=24):
        expires_at = timezone.now() + timedelta(hours=hours)
        qr = QRLink(
            qr_id=qr_id,
            merchant=self.merchant,
            employee=self.employee,
            nonce=nonce,
            expires_at=expires_at,
            signature="0" * 16,
        )
        qr.signature = sign_qr(
            self.merchant.merchant_id,
            self.employee.employee_id,
            nonce,
            expires_at,
        )
        qr.save()
        return qr

    def create_payment(self, qr, key="test-idempotency-key", tip_amount="31.85", **extra):
        body = {
            "qr_id": qr.qr_id,
            "tip_amount": tip_amount,
            "payment_method": "SBP",
            "cover_service_fee": False,
            "idempotency_key": key,
        }
        body.update(extra)
        return self.client.post(
            "/v1/tips",
            data=body,
            content_type="application/json",
        )

    def test_successful_tip_payment(self):
        qr = self.make_qr()
        response = self.create_payment(qr)
        self.assertEqual(response.status_code, 201)
        payment = Payment.objects.get(pk=response.json()["payment_id"])
        self.assertEqual(payment.tip, Decimal("31.85"))
        self.assertEqual(payment.amount_total, Decimal("31.85"))
        self.assertEqual(payment.service_fee, Decimal("0.64"))
        self.assertEqual(payment.employee_net_amount, Decimal("31.21"))
        with patch("tips.services._gateway_result", return_value=(Payment.Status.SUCCESS, "")):
            confirmed = self.client.post(
                "/v1/payments/{}/confirm".format(payment.payment_id),
                data={"confirm_token": response.json()["confirm_token"]},
                content_type="application/json",
            )
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.json()["status"], Payment.Status.SUCCESS)
        self.assertEqual(payment.audit_events.count(), 3)

    def test_declined_gateway_payment(self):
        nonce = next(
            "{:06x}".format(number)
            for number in range(1, 0x1000000)
            if int(hashlib.sha256(("qr_003" + "{:06x}".format(number)).encode()).hexdigest(), 16) % 10 == 8
        )
        qr = self.make_qr(qr_id="qr_003", nonce=nonce)
        created = self.create_payment(qr, "decline-idempotency-key")
        payment = Payment.objects.get(pk=created.json()["payment_id"])
        confirmed = self.client.post(
            "/v1/payments/{}/confirm".format(payment.payment_id),
            data={"confirm_token": created.json()["confirm_token"]},
            content_type="application/json",
        )
        self.assertEqual(confirmed.json()["status"], Payment.Status.DECLINED)
        self.assertEqual(confirmed.json()["error_code"], "CARD_DECLINED")

    def test_invalid_qr_creates_no_payment(self):
        qr = self.make_qr()
        qr.signature = "f" * 16
        qr.save(update_fields=["signature"])
        response = self.create_payment(qr)
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error_code"], "INVALID_QR")
        self.assertEqual(Payment.objects.count(), 0)

    def test_idempotent_retry_returns_existing_payment(self):
        qr = self.make_qr()
        first = self.create_payment(qr, "repeat-idempotency-key")
        second = self.create_payment(qr, "repeat-idempotency-key")
        replay = self.create_payment(qr, "different-replay-idempotency-key")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json()["payment_id"], second.json()["payment_id"])
        self.assertEqual(replay.status_code, 409)
        self.assertEqual(replay.json()["error_code"], "QR_USED")
        self.assertEqual(Payment.objects.count(), 1)

    def test_cancel_before_confirmation_and_reject_cancel_after_pending(self):
        qr = self.make_qr()
        created = self.create_payment(qr)
        payment_id = created.json()["payment_id"]
        canceled = self.client.post(
            "/v1/payments/{}/cancel".format(payment_id),
            data={"confirm_token": created.json()["confirm_token"]},
            content_type="application/json",
        )
        self.assertEqual(canceled.json()["status"], Payment.Status.CANCELED)

        qr2 = self.make_qr(qr_id="qr_002", nonce="000002")
        pending_payment = self.create_payment(qr2, "cancel-pending-idempotency-key")
        with patch("tips.services._gateway_result", return_value=(Payment.Status.PENDING, "GATEWAY_TIMEOUT")):
            confirmed = self.client.post(
                "/v1/payments/{}/confirm".format(pending_payment.json()["payment_id"]),
                data={"confirm_token": pending_payment.json()["confirm_token"]},
                content_type="application/json",
            )
        self.assertEqual(confirmed.json()["status"], Payment.Status.PENDING)
        self.assertTrue(
            Payment.objects.get(pk=pending_payment.json()["payment_id"])
            .audit_events.filter(action="payment_timeout")
            .exists()
        )
        rejected = self.client.post(
            "/v1/payments/{}/cancel".format(pending_payment.json()["payment_id"]),
            data={"confirm_token": pending_payment.json()["confirm_token"]},
            content_type="application/json",
        )
        self.assertEqual(rejected.status_code, 409)
        self.assertEqual(rejected.json()["error_code"], "CANCEL_NOT_ALLOWED")

    def test_expired_qr_returns_gone(self):
        qr = self.make_qr(hours=-1)
        response = self.client.get("/v1/qr/{}".format(qr.qr_id))
        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.json()["error_code"], "QR_EXPIRED")

    def test_owner_can_generate_signed_qr_with_payment_link(self):
        response = self.client.post(
            "/v1/qr",
            data={"employee_id": "e_001"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        body = response.json()
        qr = QRLink.objects.get(pk=body["qr_id"])
        self.assertTrue(body["payment_url"].endswith("?qr={}".format(qr.qr_id)))
        self.assertTrue(body["qr_image_svg_base64"])
        self.assertEqual(body["qr_image_url"], "http://testserver/v1/qr/{}/image".format(qr.qr_id))
        svg = ET.fromstring(base64.b64decode(body["qr_image_svg_base64"]))
        self.assertEqual(svg.get("width"), "196px")
        self.assertEqual(svg.get("height"), "196px")
        self.assertEqual(svg.get("fill"), "#2E1E14")
        svg_namespace = "http://www.w3.org/2000/svg"
        self.assertEqual(svg[0].tag, "{{{}}}rect".format(svg_namespace))
        self.assertEqual(svg[0].get("fill"), "#FFFFFF")
        qr_path = svg.find("{{{}}}path".format(svg_namespace))
        self.assertIsNotNone(qr_path)
        self.assertEqual(qr_path.get("fill"), "#2E1E14")
        icon = svg.find("{{{}}}svg".format(svg_namespace))
        self.assertIsNotNone(icon)
        self.assertEqual(icon.get("viewBox"), "0 0 44 44")
        self.assertEqual(icon.get("fill"), "none")
        self.assertEqual([element.tag for element in icon], [
            "{{{}}}rect".format(svg_namespace),
            "{{{}}}rect".format(svg_namespace),
            "{{{}}}path".format(svg_namespace),
        ])
        self.assertEqual([element.get("fill") for element in icon], ["#7A4A22", None, "#FFF6EC"])
        self.assertEqual([element.get("stroke") for element in icon], [None, "#FBF6F0", "#FFF6EC"])
        self.assertEqual(icon.get("width"), icon.get("height"))
        view_x, view_y, view_width, view_height = map(float, svg.get("viewBox").split())
        self.assertAlmostEqual(float(icon.get("x")) + float(icon.get("width")) / 2, view_x + view_width / 2)
        self.assertAlmostEqual(float(icon.get("y")) + float(icon.get("height")) / 2, view_y + view_height / 2)
        self.assertEqual(body["merchant_name"], self.merchant.name)
        self.assertEqual(body["employee_name"], "Анна")
        self.assertNotIn("base_amount", body)

        image_response = self.client.get("/v1/qr/{}/image".format(qr.qr_id))
        self.assertEqual(image_response.status_code, 200)
        self.assertEqual(image_response["Content-Type"], "image/png")
        image = Image.open(io.BytesIO(image_response.content))
        self.assertEqual(image.format, "PNG")
        self.assertEqual(image.size, (196, 196))

    def test_employee_photo_returns_png_placeholder_and_accepts_png_upload(self):
        qr = self.make_qr()
        photo_url = "/v1/qr/{}/employee-photo".format(qr.qr_id)

        placeholder = self.client.get(photo_url)
        self.assertEqual(placeholder.status_code, 200)
        self.assertEqual(placeholder["Content-Type"], "image/png")
        self.assertEqual(Image.open(io.BytesIO(placeholder.content)).format, "PNG")

        image_buffer = io.BytesIO()
        Image.new("RGB", (32, 32), "#336699").save(image_buffer, format="PNG")
        upload = SimpleUploadedFile("employee.png", image_buffer.getvalue(), content_type="image/png")
        uploaded = self.client.post(photo_url, {"photo": upload})
        self.assertEqual(uploaded.status_code, 200)
        self.assertEqual(uploaded.json()["employee_photo_url"], "http://testserver" + photo_url)

        qr.employee.refresh_from_db()
        self.assertTrue(qr.employee.photo_png)
        stored_image = self.client.get(photo_url)
        self.assertEqual(stored_image.status_code, 200)
        self.assertEqual(stored_image.content, bytes(qr.employee.photo_png))
        self.assertEqual(Image.open(io.BytesIO(stored_image.content)).format, "PNG")

    def test_qr_returns_compliments_and_payment_persists_multiple_choices(self):
        qr = self.make_qr()
        qr_response = self.client.get("/v1/qr/{}".format(qr.qr_id))
        self.assertEqual(qr_response.status_code, 200)
        self.assertEqual(
            {option["value"] for option in qr_response.json()["compliment_options"]},
            set(Payment.Compliment.values),
        )
        self.assertEqual(
            qr_response.json()["employee_photo_url"],
            "http://testserver/v1/qr/{}/employee-photo".format(qr.qr_id),
        )

        response = self.create_payment(
            qr,
            "multiple-compliment-idempotency",
            compliments=["ATTENTIVE", "FAST"],
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(set(response.json()["compliments"]), {"ATTENTIVE", "FAST"})
        payment = Payment.objects.get(pk=response.json()["payment_id"])
        self.assertEqual(set(payment.compliments.values_list("code", flat=True)), {"ATTENTIVE", "FAST"})
        self.assertEqual(payment.compliment, "")

    @override_settings(CSRF_TRUSTED_ORIGINS=["http://localhost:8000"])
    def test_payment_link_returns_qr_data_json_and_csrf_protects_payment(self):
        client = Client(enforce_csrf_checks=True)
        qr = self.make_qr()
        csrf_response = client.get("/health")
        self.assertEqual(csrf_response.status_code, 200)
        self.assertEqual(csrf_response.json()["status"], "ok")
        self.assertTrue(csrf_response.json()["csrfToken"])
        self.assertIn("csrftoken", client.cookies)

        response = client.get("/pay/?qr={}".format(qr.qr_id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.json()["qr_id"], qr.qr_id)
        self.assertEqual(response.json()["payment_url"], "http://testserver/pay/?qr={}".format(qr.qr_id))
        self.assertIn("tip_options", response.json())
        self.assertIn("payment_methods", response.json())

        created = client.post(
            "/v1/tips",
            data={
                "qr_id": qr.qr_id,
                "tip_amount": "31.85",
                "payment_method": "SBP",
                "cover_service_fee": False,
                "idempotency_key": "csrf-protected-test-key",
            },
            content_type="application/json",
            HTTP_X_CSRFTOKEN=csrf_response.json()["csrfToken"],
            HTTP_ORIGIN="http://localhost:8000",
        )
        self.assertEqual(created.status_code, 201)

    def test_payment_link_requires_a_valid_qr(self):
        missing_qr = self.client.get("/pay/")
        self.assertEqual(missing_qr.status_code, 422)
        self.assertEqual(missing_qr.json()["error_code"], "INVALID_QR")

        unknown_qr = self.client.get("/pay/?qr=qr_missing")
        self.assertEqual(unknown_qr.status_code, 404)
        self.assertEqual(unknown_qr.json()["error_code"], "INVALID_QR")

    @override_settings(SECURE_SSL_REDIRECT=True)
    def test_cors_allows_any_origin_and_credentialed_preflight(self):
        origin = "https://frontend.example"
        response = self.client.get("/health", HTTP_ORIGIN=origin)
        self.assertEqual(response["Access-Control-Allow-Origin"], origin)
        self.assertEqual(response["Access-Control-Allow-Credentials"], "true")

        preflight = self.client.options(
            "/v1/tips",
            HTTP_ORIGIN=origin,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type,x-csrftoken",
        )
        self.assertEqual(preflight.status_code, 200)
        self.assertEqual(preflight["Access-Control-Allow-Origin"], origin)
        self.assertIn("POST", preflight["Access-Control-Allow-Methods"])
        self.assertIn("x-csrftoken", preflight["Access-Control-Allow-Headers"])

    def test_custom_tip_amount_is_exact_and_capped(self):
        qr = self.make_qr()
        response = self.create_payment(qr, "custom-amount-idempotency-key", tip_amount="12.34")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["tip_amount"], "12.34")
        rejected = self.create_payment(qr, "oversize-custom-idempotency-key", tip_amount="1000000.01")
        self.assertEqual(rejected.status_code, 422)
        self.assertEqual(rejected.json()["error_code"], "TIP_OUT_OF_RANGE")

    def test_owner_invites_employee_and_employee_accepts_invitation(self):
        invitation = self.client.post(
            "/v1/employees",
            data={
                "name": "Иван",
                "email": "ivan@example.com",
                "phone": "+79990000003",
                "role": Employee.Role.BARTENDER,
                "payout_last4": "4567",
            },
            content_type="application/json",
        )
        self.assertEqual(invitation.status_code, 201)
        body = invitation.json()
        employee = Employee.objects.get(pk=body["employee_id"])
        self.assertEqual(employee.payment_details, "****4567")
        self.assertNotEqual(employee.invite_token_hash, body["invite_token"])
        accepted = self.client.post(
            "/v1/employees/{}/accept".format(employee.employee_id),
            data={"invite_token": body["invite_token"], "password": "valid-password-456"},
            content_type="application/json",
        )
        self.assertEqual(accepted.status_code, 200)
        employee.refresh_from_db()
        self.assertIsNotNone(employee.user)
        self.assertEqual(employee.role, Employee.Role.BARTENDER)
        self.assertEqual(employee.user.profile.phone, "+79990000003")
        self.assertEqual(employee.user.profile.email, "ivan@example.com")

    def test_owner_employee_and_daily_reports_are_scoped_and_aggregated(self):
        qr = self.make_qr()
        response = self.create_payment(qr)
        payment = Payment.objects.get(pk=response.json()["payment_id"])
        payment.status = Payment.Status.SUCCESS
        payment.save(update_fields=["status"])
        day = timezone.localdate().isoformat()

        merchant_report = self.client.get(
            "/v1/reports/tips",
            {"merchant_id": "m_001", "from": day, "to": day},
        )
        self.assertEqual(merchant_report.status_code, 200)
        self.assertEqual(merchant_report.json()["tips_total"], "31.85")
        self.assertEqual(merchant_report.json()["avg_tip_amount"], "31.85")
        self.assertEqual(merchant_report.json()["success_rate"], 1.0)

        daily_report = self.client.get(
            "/v1/reports/tips/daily",
            {"merchant_id": "m_001", "from": day, "to": day},
        )
        self.assertEqual(daily_report.json()["daily"][0]["tips_total"], "31.85")

        self.client.force_login(self.employee.user)
        employee_report = self.client.get(
            "/v1/reports/tips",
            {"employee_id": "e_001", "from": day, "to": day},
        )
        self.assertEqual(employee_report.status_code, 200)
        self.assertEqual(employee_report.json()["avg_tip_amount"], "31.85")

    def test_fee_ratings_compliment_and_goal_are_recorded_and_progress_updates(self):
        create_goal = self.client.post(
            "/v1/goals",
            data={
                "employee_id": self.employee.employee_id,
                "title": "Новый кофейный аппарат",
                "description": "Для кофейной станции",
                "target_amount": "1000.00",
            },
            content_type="application/json",
        )
        self.assertEqual(create_goal.status_code, 201)
        goal_id = create_goal.json()["goal_id"]
        qr = self.make_qr()
        qr_data = self.client.get("/v1/qr/{}".format(qr.qr_id)).json()
        self.assertEqual(qr_data["active_goals"][0]["goal_id"], goal_id)
        self.assertEqual(qr_data["active_goals"][0]["collected_amount"], "0.00")
        self.assertEqual(qr_data["employee_role"], Employee.Role.WAITER)
        response = self.create_payment(
            qr,
            "goal-feature-idempotency-key",
            tip_amount="100.00",
            payment_method="CARD",
            cover_service_fee=True,
            goal_id=goal_id,
            service_rating=5,
            restaurant_rating=4,
            restaurant_comment="Отличное меню",
            compliment="ATTENTIVE",
            employee_comment="Спасибо за помощь с выбором",
        )
        self.assertEqual(response.status_code, 201)
        payment = Payment.objects.get(pk=response.json()["payment_id"])
        self.assertEqual(payment.amount_total, Decimal("105.00"))
        self.assertEqual(payment.service_fee, Decimal("5.00"))
        self.assertEqual(payment.employee_net_amount, Decimal("100.00"))
        self.assertEqual(payment.payment_method, Payment.Method.CARD)
        self.assertEqual(payment.restaurant_rating, 4)
        self.assertEqual(payment.compliment, Payment.Compliment.ATTENTIVE)
        self.assertEqual(payment.goal_id, goal_id)
        self.assertEqual(payment.goal.collected_amount, Decimal("0.00"))

        with patch("tips.services._gateway_result", return_value=(Payment.Status.SUCCESS, "")):
            confirmed = self.client.post(
                "/v1/payments/{}/confirm".format(payment.payment_id),
                data={"confirm_token": response.json()["confirm_token"]},
                content_type="application/json",
            )
        self.assertEqual(confirmed.json()["status"], Payment.Status.SUCCESS)
        goal = TipGoal.objects.get(pk=goal_id)
        self.assertEqual(goal.collected_amount, Decimal("100.00"))
        self.assertEqual(goal.progress_pct, 10)

    def test_bank_commission_rates_and_payer_options(self):
        rates = {"SBP": Decimal("2.00"), "CARD": Decimal("5.00"), "SBERPAY": Decimal("5.00")}
        qr_response = self.client.post(
            "/v1/qr",
            data={"employee_id": self.employee.employee_id},
            content_type="application/json",
        )
        self.assertEqual(qr_response.status_code, 201)
        available_methods = {
            method["value"]: method["bank_fee_percent"]
            for method in qr_response.json()["payment_methods"]
        }
        self.assertEqual(available_methods, {"SBP": 2, "CARD": 5, "SBERPAY": 5})

        for index, (method, rate) in enumerate(rates.items()):
            for payer_index, covered_by_client in enumerate((True, False)):
                qr_number = index * 2 + payer_index
                qr = self.make_qr(
                    qr_id="qr_fee_{}".format(qr_number),
                    nonce="{:06x}".format(qr_number + 10),
                )
                payment_response = self.create_payment(
                    qr,
                    "fee-option-{}-{}".format(index, "client" if covered_by_client else "employee"),
                    tip_amount="100.00",
                    payment_method=method,
                    cover_service_fee=covered_by_client,
                )
                self.assertEqual(payment_response.status_code, 201)
                body = payment_response.json()
                payment = Payment.objects.get(pk=body["payment_id"])
                fee = Decimal("100.00") * rate / Decimal("100")
                self.assertEqual(payment.service_fee, fee)
                self.assertEqual(payment.amount_total, Decimal("100.00") + (fee if covered_by_client else Decimal("0.00")))
                self.assertEqual(payment.employee_net_amount, Decimal("100.00") - (Decimal("0.00") if covered_by_client else fee))
                self.assertEqual(body["commission_payer"], "CLIENT" if covered_by_client else "EMPLOYEE")
                self.assertEqual(Decimal(body["employee_net_amount"]), payment.employee_net_amount)
                conflicting_payer = self.create_payment(
                    qr,
                    "fee-option-{}-{}".format(index, "client" if covered_by_client else "employee"),
                    tip_amount="100.00",
                    payment_method=method,
                    cover_service_fee=not covered_by_client,
                )
                self.assertEqual(conflicting_payer.status_code, 409)
                self.assertEqual(conflicting_payer.json()["error_code"], "IDEMPOTENCY_CONFLICT")

        invalid_qr = self.make_qr(qr_id="qr_no_apple", nonce="000020")
        apple_pay = self.create_payment(
            invalid_qr,
            "apple-pay-is-disabled",
            payment_method="APPLE_PAY",
        )
        self.assertEqual(apple_pay.status_code, 422)
        self.assertEqual(apple_pay.json()["error_code"], "PAYMENT_METHOD_INVALID")

    def test_admin_can_create_tip_goal_without_manual_id(self):
        admin_user = User.objects.create_superuser(
            username="admin@example.com",
            email="admin@example.com",
            password="Admin-password-123",
        )
        self.client.force_login(admin_user)

        response = self.client.post(
            "/admin/tips/tipgoal/add/",
            {
                "employee": self.employee.employee_id,
                "title": "Новая цель",
                "description": "",
                "target_amount": "1000.00",
                "is_active": "on",
            },
        )

        self.assertEqual(response.status_code, 302)
        goal = TipGoal.objects.get(title="Новая цель")
        self.assertRegex(goal.goal_id, r"^g_[0-9a-f]{32}$")

    def test_merchant_registration_requires_phone_and_creates_profile(self):
        response = self.client.post(
            "/v1/merchants/register",
            data={
                "name": "Новое кафе",
                "email": "new-merchant@example.com",
                "phone": "+79990000009",
                "password": "valid-password-789",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(username="new-merchant@example.com")
        self.assertEqual(user.profile.phone, "+79990000009")
        self.assertEqual(user.profile.email, "new-merchant@example.com")

    def test_profile_email_must_be_valid_limited_and_case_insensitively_unique(self):
        user = User.objects.create_user(username="another@example.com", password="valid-password-abc")
        invalid = UserProfile(user=user, email="not-an-email", phone="+79990000010")
        with self.assertRaises(ValidationError):
            invalid.full_clean()

        too_long_email = "{}@example.com".format("a" * 250)
        too_long = UserProfile(user=user, email=too_long_email, phone="+79990000010")
        with self.assertRaises(ValidationError):
            too_long.full_clean()

        duplicate = UserProfile(user=user, email="OWNER@EXAMPLE.COM", phone="+79990000010")
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_merchant_registration_rejects_duplicate_email_case_insensitively(self):
        response = self.client.post(
            "/v1/merchants/register",
            data={
                "name": "Кафе-дубликат",
                "email": "OWNER@EXAMPLE.COM",
                "phone": "+79990000011",
                "password": "valid-password-789",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error_code"], "EMAIL_EXISTS")


@override_settings(TIP_QR_SECRET="test-secret")
class SeedCsvImportTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.data_dir = Path(self.temp_dir.name)
        self._write_csv("merchants.csv", "merchant_id,name,status,description\nm_101,Cafe,ACTIVE,Source\n")
        self._write_csv(
            "employees.csv",
            "employee_id,merchant_id,name,payment_details\ne_101,m_101,Alex,****1234\n",
        )
        expires_at = timezone.now() + timedelta(days=1)
        self._write_csv(
            "qr_links.csv",
            "qr_id,merchant_id,employee_id,receipt_id,nonce,exp,signature\n"
            "qr_0101,m_101,e_101,r_1,abcdef,{},{}\n".format(
                expires_at.isoformat().replace("+00:00", "Z"),
                "a" * 16,
            ),
        )
        self._write_csv(
            "payments.csv",
            "payment_id,merchant_id,employee_id,amount,tip,status,timestamp\n"
            "p_0101,m_101,e_101,100.00,5.00,SUCCESS,{}\n".format(
                timezone.now().isoformat().replace("+00:00", "Z")
            ),
        )

    def _write_csv(self, filename, content):
        (self.data_dir / filename).write_text(content, encoding="utf-8")

    def test_dry_run_validates_without_writing(self):
        output = StringIO()
        call_command("import_seed_csv", data_dir=self.data_dir, dry_run=True, stdout=output)
        self.assertIn("Would merchants: 1 created, 0 skipped", output.getvalue())
        self.assertEqual(Merchant.objects.count(), 0)
        self.assertEqual(Employee.objects.count(), 0)
        self.assertEqual(QRLink.objects.count(), 0)
        self.assertEqual(Payment.objects.count(), 0)

    def test_import_is_idempotent_and_preserves_existing_changes(self):
        call_command("import_seed_csv", data_dir=self.data_dir, stdout=StringIO())
        merchant = Merchant.objects.get(pk="m_101")
        employee = Employee.objects.get(pk="e_101")
        qr = QRLink.objects.get(pk="qr_0101")
        payment = Payment.objects.get(pk="p_0101")
        merchant.name = "Locally edited cafe"
        merchant.save(update_fields=["name"])
        employee.name = "Locally edited employee"
        employee.save(update_fields=["name"])

        call_command("import_seed_csv", data_dir=self.data_dir, stdout=StringIO())

        merchant.refresh_from_db()
        employee.refresh_from_db()
        qr.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(merchant.name, "Locally edited cafe")
        self.assertEqual(employee.name, "Locally edited employee")
        self.assertIsNone(employee.user_id)
        self.assertTrue(verify_qr_signature(qr))
        self.assertEqual(qr.source_metadata["row"]["receipt_id"], "r_1")
        self.assertEqual(payment.tip, Decimal("5.00"))
        self.assertEqual(payment.source_metadata["row"]["amount"], "100.00")
        self.assertEqual(payment.audit_events.get(action="payment_imported").at, payment.created_at)
        self.assertEqual(Payment.objects.count(), 1)

    def test_invalid_foreign_key_prevents_all_writes(self):
        self._write_csv(
            "employees.csv",
            "employee_id,merchant_id,name,payment_details\ne_101,m_999,Alex,****1234\n",
        )
        with self.assertRaises(CommandError):
            call_command("import_seed_csv", data_dir=self.data_dir, stdout=StringIO())
        self.assertEqual(Merchant.objects.count(), 0)
        self.assertEqual(Employee.objects.count(), 0)

    def test_duplicate_nonce_prevents_all_writes(self):
        qr_file = self.data_dir / "qr_links.csv"
        qr_rows = qr_file.read_text(encoding="utf-8")
        self._write_csv(
            "qr_links.csv",
            qr_rows + "qr_0102,m_101,e_101,r_2,ABCDEF,2027-01-01T00:00:00Z,bbbbbbbbbbbbbbbb\n",
        )
        with self.assertRaises(CommandError):
            call_command("import_seed_csv", data_dir=self.data_dir, stdout=StringIO())
        self.assertEqual(Merchant.objects.count(), 0)
        self.assertEqual(Employee.objects.count(), 0)
        self.assertEqual(QRLink.objects.count(), 0)
