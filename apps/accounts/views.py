"""Authentication (SRS FR-STU-01/02, SEC-08)."""
import secrets

from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (PasswordResetCompleteView, PasswordResetConfirmView,
                                       PasswordResetDoneView, PasswordResetView)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from apps.accounts.forms import (RegistrationForm, StyledAuthenticationForm,
                                 StyledPasswordChangeForm)
from apps.accounts.models import LoginAttempt, User
from apps.core.utils import client_ip
from apps.institutions.models import Shortlist
from apps.notifications.services import send_email

MAX_FAILURES = 5      # SRS SEC-08
LOCKOUT_MINUTES = 15


def _merge_shortlist(request, user, key=None):
    """SRS FR-COU-07 — session shortlist merges into the account on login.

    The key must be captured *before* login because Django cycles the session key.
    """
    key = key or request.session.session_key
    if not key:
        return
    for item in Shortlist.objects.filter(session_key=key, user__isnull=True):
        exists = Shortlist.objects.filter(user=user, course=item.course,
                                          university=item.university).exists()
        if exists:
            item.delete()
        else:
            item.user = user
            item.session_key = ""
            item.save(update_fields=["user", "session_key"])


def register(request):
    if request.user.is_authenticated:
        return redirect("portal:home")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        link = request.build_absolute_uri(
            f"/accounts/verify/{user.verification_token}/")
        send_email(
            subject="Verify your Dream Spot Global account",
            to=user.email,
            body=(f"Dear {user.first_name},\n\nPlease verify your email address:\n{link}\n\n"
                  "Dream Spot Global"))
        messages.success(request, "Account created. Please check your email to verify "
                                  "your address, then sign in.")
        return redirect("accounts:login")
    return render(request, "accounts/register.html",
                  {"form": form, "meta_title": "Create your student account"})


def verify_email(request, token):
    user = get_object_or_404(User, verification_token=token)
    user.email_verified = True
    user.verification_token = ""
    user.save(update_fields=["email_verified", "verification_token"])
    messages.success(request, "Your email is verified. You can sign in now.")
    return redirect("accounts:login")


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home" if request.user.is_staff_member else "portal:home")
    form = StyledAuthenticationForm(request, data=request.POST or None)
    if request.method == "POST":
        identifier = (request.POST.get("username") or "").lower()
        if LoginAttempt.recent_failures(identifier, LOCKOUT_MINUTES) >= MAX_FAILURES:
            messages.error(request, "Too many failed attempts. Please try again in "
                                    f"{LOCKOUT_MINUTES} minutes.")
            return render(request, "accounts/login.html",
                          {"form": form, "meta_title": "Sign in"})
        previous_session_key = request.session.session_key
        user = authenticate(request, username=identifier,
                            password=request.POST.get("password"))
        LoginAttempt.objects.create(identifier=identifier, ip_address=client_ip(request),
                                    successful=bool(user))
        if user is not None:
            auth_login(request, user, backend="apps.accounts.backends.EmailOrUsernameBackend")
            user.last_seen = timezone.now()
            user.save(update_fields=["last_seen"])
            if user.is_staff_member:
                request.session.set_expiry(
                    __import__("django.conf", fromlist=["settings"])
                    .settings.STAFF_SESSION_COOKIE_AGE)
            _merge_shortlist(request, user, previous_session_key)
            nxt = request.GET.get("next")
            if nxt:
                return redirect(nxt)
            return redirect("dashboard:home" if user.is_staff_member else "portal:home")
        messages.error(request, "Incorrect email or password.")
    return render(request, "accounts/login.html", {"form": form, "meta_title": "Sign in"})


def logout_view(request):
    auth_logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("core:home")


@login_required
def change_password(request):
    form = StyledPasswordChangeForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        auth_login(request, user, backend="apps.accounts.backends.EmailOrUsernameBackend")
        messages.success(request, "Your password has been updated.")
        return redirect("portal:profile" if not user.is_staff_member else "dashboard:home")
    return render(request, "accounts/change_password.html",
                  {"form": form, "meta_title": "Change password"})


class BrandPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("accounts:password_reset_done")


class BrandPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class BrandPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("accounts:password_reset_complete")


class BrandPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"
