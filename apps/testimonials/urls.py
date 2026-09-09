from django.urls import path

from apps.testimonials import views

app_name = "testimonials"
urlpatterns = [path("", views.testimonial_list, name="list")]
