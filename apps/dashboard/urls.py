from django.urls import path

from apps.dashboard import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("charts.json", views.chart_data, name="charts"),

    path("leads/", views.lead_list, name="lead_list"),
    path("leads/board/", views.lead_kanban, name="lead_kanban"),
    path("leads/bulk/", views.lead_bulk, name="lead_bulk"),
    path("leads/<int:pk>/", views.lead_detail, name="lead_detail"),
    path("leads/<int:pk>/move/", views.lead_move, name="lead_move"),

    path("students/", views.student_list, name="student_list"),
    path("students/<int:pk>/", views.student_detail, name="student_detail"),

    path("applications/", views.application_list, name="application_list"),
    path("applications/new/", views.application_create, name="application_create"),
    path("applications/<int:pk>/", views.application_detail, name="application_detail"),

    path("documents/", views.document_queue, name="document_queue"),
    path("documents/<int:pk>/review/", views.document_review, name="document_review"),
    path("documents/<int:pk>/download/", views.document_download, name="document_download"),

    path("appointments/", views.appointment_list, name="appointment_list"),
    path("appointments/availability/", views.availability_view, name="availability"),
    path("appointments/availability/<int:pk>/delete/", views.availability_delete,
         name="availability_delete"),

    path("enquiries/", views.enquiry_list, name="enquiries"),
    path("events/<int:pk>/registrations/", views.event_registrations,
         name="event_registrations"),
    path("newsletter/", views.newsletter_list, name="newsletter"),

    path("users/", views.user_list, name="user_list"),
    path("users/new/", views.user_edit, name="user_create"),
    path("users/<int:pk>/", views.user_edit, name="user_edit"),
    path("users/<int:pk>/toggle/", views.user_toggle, name="user_toggle"),
    path("roles/", views.roles_view, name="roles"),
    path("settings/", views.settings_view, name="settings"),
    path("audit-log/", views.audit_log, name="audit"),
    path("reports/", views.reports, name="reports"),

    path("content/<str:key>/", views.content_list, name="content_list"),
    path("content/<str:key>/new/", views.content_edit, name="content_create"),
    path("content/<str:key>/<int:pk>/", views.content_edit, name="content_edit"),
    path("content/<str:key>/<int:pk>/delete/", views.content_delete, name="content_delete"),
]
