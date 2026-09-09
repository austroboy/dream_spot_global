from django.urls import path

from apps.institutions import views

app_name = "institutions"

urlpatterns = [
    path("courses/", views.course_list, name="course_list"),
    path("courses/<slug:slug>/", views.course_detail, name="course_detail"),
    path("universities/", views.university_list, name="university_list"),
    path("universities/<slug:slug>/", views.university_detail, name="university_detail"),
    path("shortlist/", views.shortlist_view, name="shortlist"),
    path("shortlist/toggle/<int:pk>/", views.toggle_shortlist, name="toggle_shortlist"),
    path("compare/", views.compare_courses, name="compare"),
]
