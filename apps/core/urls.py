from django.urls import path

from apps.core import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("about/why-choose-us/", views.why_us, name="why_us"),
    path("about/team/", views.team, name="team"),
    path("contact/", views.contact, name="contact"),
    path("thank-you/", views.thank_you, name="thank_you"),
    path("search/", views.search, name="search"),
    path("enquiry/", views.quick_enquiry, name="quick_enquiry"),
    path("newsletter/", views.newsletter_signup, name="newsletter"),
    path("newsletter/confirm/<str:token>/", views.newsletter_confirm, name="newsletter_confirm"),
]
