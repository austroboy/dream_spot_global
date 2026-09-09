def unread_notifications(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"unread_notifications": 0}
    from apps.notifications.models import Notification
    return {"unread_notifications":
            Notification.objects.filter(recipient=user, is_read=False).count()}
