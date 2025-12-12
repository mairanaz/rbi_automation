from django.db import models
from django.conf import settings
# Create your models here.
class Analysis(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("in_progress", "In Progress"),
        ("awaiting_regions", "Awaiting Region Selection"),
        ("ready_to_generate", "Ready To Generate"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    # boleh kekalkan kalau nak guna juga Django user satu hari nanti
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="analyses",
        null=True,
        blank=True,
    )

    # 🆕 User dari RBI_SERVER
    external_user_id = models.PositiveIntegerField(null=True, blank=True)
    external_user_email = models.CharField(max_length=255, null=True, blank=True)
    external_user_name = models.CharField(max_length=255, null=True, blank=True)

    file = models.FileField(upload_to="analysis/pdf/")
    original_filename = models.CharField(max_length=255)
    status = models.CharField(
        max_length=32, choices=STATUS_CHOICES, default="awaiting_regions"
    )
    workbook_path = models.CharField(max_length=500, null=True, blank=True)
    pptx_path = models.CharField(max_length=500, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

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

    # normalized coordinates 0–1
    x1 = models.FloatField()
    y1 = models.FloatField()
    x2 = models.FloatField()
    y2 = models.FloatField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # untuk Design Data & BOM, kita expect satu je per analysis
        # slide_image boleh banyak (kalau next time nak multi selection)
        indexes = [
            models.Index(fields=["analysis", "step_type"]),
        ]

    def __str__(self):
        return f"{self.analysis_id} - {self.step_type} - p{self.page.page_number}"