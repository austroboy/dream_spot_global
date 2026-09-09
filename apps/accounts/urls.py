from django.urls import path

from apps.accounts import views

app_name = "accounts"
urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("verify/<str:token>/", views.verify_email, name="verify"),
    path("password/change/", views.change_password, name="change_password"),
    path("password-reset/", views.BrandPasswordResetView.as_view(), name="password_reset"),
    path("password-reset/done/", views.BrandPasswordResetDoneView.as_view(),
         name="password_reset_done"),
    path("password-reset/<uidb64>/<token>/", views.BrandPasswordResetConfirmView.as_view(),
         name="password_reset_confirm"),
    path("password-reset/complete/", views.BrandPasswordResetCompleteView.as_view(),
         name="password_reset_complete"),
]
