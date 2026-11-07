from uuid import uuid4

from django.contrib import admin

from .models import AuditEvent, Employee, Merchant, Payment, QRLink, TipGoal, TipReport, UserProfile


@admin.action(description="Активировать выбранных мерчантов")
def activate_merchants(modeladmin, request, queryset):
    queryset.update(status=Merchant.Status.ACTIVE)


@admin.action(description="Заблокировать выбранных мерчантов")
def block_merchants(modeladmin, request, queryset):
    queryset.update(status=Merchant.Status.BLOCKED)


@admin.register(Merchant)
class MerchantAdmin(admin.ModelAdmin):
    list_display = ("merchant_id", "name", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("merchant_id", "name")
    actions = (activate_merchants, block_merchants)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "name", "role", "merchant", "email", "phone", "payment_details")
    readonly_fields = ("payment_details", "invite_token_hash")


@admin.register(QRLink)
class QRLinkAdmin(admin.ModelAdmin):
    list_display = ("qr_id", "merchant", "employee", "expires_at", "used_at")
    readonly_fields = ("signature", "nonce")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("payment_id", "merchant", "employee", "tip", "service_fee", "payment_method", "status", "created_at")
    list_filter = ("status", "payment_method", "merchant")
    readonly_fields = ("idempotency_key",)


@admin.register(TipReport)
class TipReportAdmin(admin.ModelAdmin):
    list_display = ("merchant", "start_date", "end_date", "tips_total", "payments_count", "success_rate")
    readonly_fields = ("merchant", "start_date", "end_date", "tips_total", "payments_count", "avg_tip_amount", "success_rate")


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "payment", "action", "from_status", "to_status", "actor", "at")
    readonly_fields = ("event_id", "payment", "qr", "action", "from_status", "to_status", "amount_total", "actor", "at", "details")


@admin.register(TipGoal)
class TipGoalAdmin(admin.ModelAdmin):
    list_display = ("goal_id", "employee", "title", "target_amount", "is_active", "created_at")
    list_filter = ("is_active", "employee__role", "employee__merchant")
    readonly_fields = ("goal_id", "created_at")

    def save_model(self, request, obj, form, change):
        if not obj.goal_id:
            obj.goal_id = "g_{}".format(uuid4().hex)
        super().save_model(request, obj, form, change)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "email", "phone")
    search_fields = ("email", "user__username", "phone")
