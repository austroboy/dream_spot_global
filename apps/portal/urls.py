from django.urls import path

from apps.portal import views

app_name = "portal"
urlpatterns = [
    path("", views.home, name="home"),
    path("profile/", views.profile, name="profile"),
    path("profile/academic/add/", views.add_academic_record, name="add_record"),
    path("profile/academic/<int:pk>/delete/", views.delete_academic_record,
         name="delete_record"),
    path("documents/", views.documents, name="documents"),
    path("documents/<int:pk>/download/", views.document_download, name="document_download"),
    path("documents/<int:pk>/delete/", views.document_delete, name="document_delete"),
    path("applications/", views.applications, name="applications"),
    path("applications/<int:pk>/", views.application_detail, name="application_detail"),
    path("appointments/", views.appointments, name="appointments"),
    path("shortlist/", views.shortlist, name="shortlist"),
    path("messages/", views.messages_view, name="messages"),
    path("notifications/", views.notifications, name="notifications"),
    path("export/", views.export_data, name="export"),
]
