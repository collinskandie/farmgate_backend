from django.db import models
from django.conf import settings
from accounts.models import Cow, Farm


class MilkRecord(models.Model):
    """
    Represents milk production records for cows.
    """
    MORNING = "morning"
    EVENING = "evening"
    SESSION_CHOICES = [
        (MORNING, "Morning"),
        (EVENING, "Evening"),
    ]
    cow = models.ForeignKey(
        Cow,
        on_delete=models.CASCADE,
        related_name="milk_records"
    )
    date = models.DateField()
    session = models.CharField(
        max_length=10,
        choices=SESSION_CHOICES
    )
    quantity_in_liters = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        help_text="Milk produced in litres"
    )
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="milk_records"
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["-date", "-created_at"]
        unique_together = ("cow", "date", "session")
        verbose_name = "Milk Record"
        verbose_name_plural = "Milk Records"

    def __str__(self):
        return f"{self.cow} | {self.date} | {self.session} | {self.quantity_in_liters}L"

class ChatSession(models.Model):
    phone = models.CharField(max_length=20, unique=True)
    farm = models.ForeignKey(
        Farm, on_delete=models.CASCADE, null=True, blank=True
    )
    step = models.CharField(max_length=50, default="start")
    data = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)
