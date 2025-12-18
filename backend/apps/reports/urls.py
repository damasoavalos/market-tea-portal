from django.urls import path
from . import views

urlpatterns = [
    path("", views.upload_form, name="reports_upload"),
    path("generate/", views.generate_from_upload, name="reports_generate"),
]
