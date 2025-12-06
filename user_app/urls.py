from django.urls import path 
from . import views


urlpatterns=[
    path('', views.user_registration, name='registration'),
    path("google/callback/", views.google_callback, name="google_callback"),
    path("auth/google/", views.google_login, name="google_login"),
    path('login/',views.login_view, name='login'),
    path('dashboard/', views.dashboard,name='dashboard'),
    path('upload/', views.upload_and_analyze, name='upload_analyze'),

    path('download/<str:analysis_id>/<str:file_type>/', views.download_file, name='download_file'),

    path("preview/<str:analysis_id>/<str:file_type>/", views.preview_file, name="preview_file"),

    path('delete/<str:analysis_id>/', views.delete_analysis, name='delete_analysis'),
]