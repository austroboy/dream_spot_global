"""Notification dispatch. Runs inline by default; swap in Celery in production (SRS FR-LED-06)."""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from apps.notifications.models import EmailTemplate, Notification

logger = logging.getLogger(__name__)


def notify_user(user, title, body="", level="info", url=""):
    if not user:
        return None
    return Notification.objects.create(recipient=user, title=title, body=body,
                                       level=level, url=url)


def send_email(subject, to, template=None, context=None, body=None, attachments=None):
    """SRS FR-LED-09 — never let a mail failure break the request."""
    context = context or {}
    to = [t for t in (to if isinstance(to, (list, tuple)) else [to]) if t]
    if not to:
        return False
    html = None
    if template:
        try:
            html = render_to_string(template, context)
        except Exception:
            logger.exception("Email template render failed: %s", template)
    text = body or ""
    try:
        msg = EmailMultiAlternatives(subject, text or " ", settings.DEFAULT_FROM_EMAIL, to)
        if html:
            msg.attach_alternative(html, "text/html")
        for name, content, mimetype in (attachments or []):
            msg.attach(name, content, mimetype)
        msg.send(fail_silently=True)
        return True
    except Exception:
        logger.exception("Email dispatch failed for %s", to)
        return False


def send_templated(key, to, context, fallback_subject="", fallback_body=""):
    """Use the DB-editable template when present, otherwise the fallback."""
    tpl = EmailTemplate.objects.filter(key=key, is_active=True).first()
    if tpl:
        subject, body = tpl.render(context)
    else:
        subject, body = fallback_subject, fallback_body
    return send_email(subject, to, body=body)


def notify_staff(subject, body, extra_emails=None):
    recipients = list(settings.NOTIFY_EMAILS) + list(extra_emails or [])
    return send_email(subject, recipients, body=body)
