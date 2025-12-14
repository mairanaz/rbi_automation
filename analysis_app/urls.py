from django.urls import path
from . import views

app_name = "analysis_app"

urlpatterns = [
    path("upload/", views.upload_analysis, name="upload"),
    path("analysis/history/", views.analysis_history, name="history"),
    path("analysis/<int:analysis_id>/detail/", views.analysis_detail, name="analysis_detail"),

    path(
        "analysis/<int:analysis_id>/select/<str:step_type>/page/<int:page_number>/",
        views.select_region,
        name="select_region",
    ),
    path(
        "analysis/<int:analysis_id>/review/",
        views.review_analysis,
        name="review_analysis",
    ),
    path(
        "analysis/<int:analysis_id>/generate/",
        views.generate_analysis,
        name="generate_analysis",
    ),

    path( "analysis/<int:analysis_id>/edit-masterfile/",views.edit_masterfile, name="edit_masterfile",),
    path("analysis/<int:analysis_id>/save-masterfile/", views.save_masterfile,name="save_masterfile",),

    path( "analysis/<int:analysis_id>/upload-corrected-masterfile/", views.upload_corrected_masterfile, name="upload_corrected_masterfile", ),
]
