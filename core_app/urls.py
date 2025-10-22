from django.urls import path
from . import views

urlpatterns = [
    path("", views.upload_drawing, name="upload_drawing"),
    path("equipments/", views.equipment_list, name="equipment_list"),
]
