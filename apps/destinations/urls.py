from django.urls import path

from apps.destinations import views

app_name = "destinations"

urlpatterns = [
    path("", views.country_list, name="list"),
    path("compare/", views.compare, name="compare"),
    path("<slug:slug>/", views.country_detail, name="detail"),
    path("<slug:slug>/universities/", views.country_universities, name="universities"),
    path("<slug:slug>/cost-of-living/", views.country_cost, name="cost"),
    path("<slug:slug>/visa-guide/", views.country_visa, name="visa"),
]
