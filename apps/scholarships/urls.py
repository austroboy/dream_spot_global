from django.urls import path

from apps.scholarships import views

app_name = "scholarships"
urlpatterns = [
    path("", views.scholarship_list, name="list"),
    path("<slug:slug>/", views.scholarship_detail, name="detail"),
]
