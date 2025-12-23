from django.db import models
from django.conf import settings
# Create your models here.


class ExternalUser(models.Model):
    provider = models.CharField(max_length=30, default="rbi_auth")
    external_id = models.CharField(max_length=64)  # Node user.id (stringkan)
    staff_id = models.CharField(max_length=20, null=True, blank=True)

    email = models.EmailField(null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)

    role_snapshot = models.CharField(max_length=32, null=True, blank=True)

    last_seen_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    avatar_url = models.URLField(max_length=500, null=True, blank=True)

    class Meta:
        unique_together = ("provider", "external_id")
        indexes = [
            models.Index(fields=["provider", "external_id"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.provider}:{self.external_id}"


class Analysis(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("awaiting_regions", "Awaiting Region Selection"),
        ("ready_to_generate", "Ready To Generate"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    file = models.FileField(upload_to="analysis/pdf/")
    original_filename = models.CharField(max_length=255)
    status = models.CharField(
        max_length=32, choices=STATUS_CHOICES, default="awaiting_regions"
    )
    workbook_path = models.CharField(max_length=500, null=True, blank=True)
    pptx_path = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    
    created_by = models.ForeignKey(
        ExternalUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="analyses",
    )

    def __str__(self):
        return f"{self.original_filename} ({self.id})"


class AnalysisPage(models.Model):
    analysis = models.ForeignKey(
        Analysis, on_delete=models.CASCADE, related_name="pages"
    )
    page_number = models.PositiveIntegerField()
    image = models.ImageField(upload_to="analysis/pages/")

    class Meta:
        unique_together = ("analysis", "page_number")
        ordering = ["page_number"]

    def __str__(self):
        return f"Analysis {self.analysis_id} - Page {self.page_number}"


class RegionSelection(models.Model):
    STEP_TYPE_CHOICES = [
        ("design_data", "Design Data"),
        ("bom", "Bill Of Material"),
        ("slide_image", "Slide Image"),
    ]

    analysis = models.ForeignKey(
        Analysis, on_delete=models.CASCADE, related_name="regions"
    )
    page = models.ForeignKey(
        AnalysisPage, on_delete=models.CASCADE, related_name="regions"
    )
    step_type = models.CharField(max_length=32, choices=STEP_TYPE_CHOICES)


    x1 = models.FloatField()
    y1 = models.FloatField()
    x2 = models.FloatField()
    y2 = models.FloatField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
    
        indexes = [
            models.Index(fields=["analysis", "step_type"]),
        ]

    def __str__(self):
        return f"{self.analysis_id} - {self.step_type} - p{self.page.page_number}"