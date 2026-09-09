from django.urls import path

from apps.faqs import views

app_name = "faqs"
urlpatterns = [path("", views.faq_list, name="list")]
