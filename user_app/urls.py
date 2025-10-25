from django.urls import path 
from . import views


urlpatterns=[
    path('', views.user_registration, name='registration'),
    path('login/',views.login_view, name='login'),
    path('dashboard/', views.dashboard,name='dashboard'),
    path('upload/', views.upload_and_analyze, name='upload_analyze'),

    path('download/<str:analysis_id>/<str:file_type>/', views.download_file, name='download_file'),




]