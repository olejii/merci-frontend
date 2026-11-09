from django.urls import path

from . import views


urlpatterns = [
    path("api/health", views.health, name="health"),
    path("pay/", views.pay_page, name="pay-page"),
    path("api/v1/auth/login", views.login_user, name="login"),
    path("api/v1/auth/logout", views.logout_user, name="logout"),
    path("api/v1/merchants/register", views.register_merchant, name="register-merchant"),
    path("api/v1/employees", views.invite_employee, name="invite-employee"),
    path("api/v1/employees/<str:employee_id>/accept", views.accept_employee_invite, name="accept-employee"),
    path("api/v1/qr", views.generate_qr, name="generate-qr"),
    path("api/v1/qr/<str:qr_id>/employee-photo", views.employee_photo, name="employee-photo"),
    path("api/v1/qr/<str:qr_id>/image", views.get_qr_image, name="get-qr-image"),
    path("api/v1/qr/<str:qr_id>", views.get_qr, name="get-qr"),
    path("api/v1/goals", views.create_tip_goal, name="create-tip-goal"),
    path("api/v1/goals/<str:goal_id>/close", views.close_tip_goal, name="close-tip-goal"),
    path("api/v1/employees/<str:employee_id>/goals", views.employee_goals, name="employee-tip-goals"),
    path("api/v1/tips", views.create_tip, name="create-tip"),
    path("api/v1/payments/<str:payment_id>/confirm", views.confirm_tip, name="confirm-tip"),
    path("api/v1/payments/<str:payment_id>/cancel", views.cancel_tip, name="cancel-tip"),
    path("api/v1/reports/tips", views.tips_report, name="tips-report"),
    path("api/v1/reports/tips/daily", views.daily_tips_report, name="daily-tips-report"),
]
