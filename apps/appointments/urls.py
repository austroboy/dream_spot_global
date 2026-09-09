from django.urls import path

from apps.appointments import views

app_name = "appointments"
urlpatterns = [
    path("", views.book_view, name="book"),
    path("confirmed/<uuid:token>/", views.success, name="success"),
    path("manage/<uuid:token>/", views.manage, name="manage"),
    path("calendar/<uuid:token>.ics", views.ics_download, name="ics"),
]
