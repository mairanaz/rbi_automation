from django.db import models

# Create your models here.


class Equipment(models.Model):
    tag_number = models.CharField(max_length=100)
    equipment_type = models.CharField(max_length=100, blank=True)
    risk_level = models.CharField(max_length=10, default='Low')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.tag_number