from django.urls import path

from apps.leads import views

app_name = "leads"
urlpatterns = [
    path("", views.assessment, name="assessment"),
    path("step/<int:step>/", views.assessment, name="assessment_step"),
]
