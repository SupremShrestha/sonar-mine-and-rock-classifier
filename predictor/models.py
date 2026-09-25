from django.conf import settings
from django.db import models


class Prediction(models.Model):
    class Source(models.TextChoices):
        SAMPLE = "sample", "Test sample"
        CSV = "csv", "CSV upload"
        PASTED = "pasted", "Pasted values"

    class Label(models.TextChoices):
        MINE = "M", "Mine"
        ROCK = "R", "Rock"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="predictions",
    )
    source = models.CharField(max_length=10, choices=Source.choices)
    source_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="File name, or a description of where the values came from.",
    )
    features = models.JSONField(help_text="The 60 sonar readings that were classified.")
    predicted_label = models.CharField(max_length=1, choices=Label.choices)
    confidence = models.FloatField(help_text="Probability of the predicted class (0-1).")
    probability_mine = models.FloatField(help_text="Probability the target is a mine (0-1).")
    true_label = models.CharField(
        max_length=1,
        choices=Label.choices,
        blank=True,
        help_text="Only known for test samples.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"{self.user} - {self.get_predicted_label_display()} ({self.confidence:.0%})"

    @property
    def probability_rock(self):
        return 1 - self.probability_mine

    @property
    def is_correct(self):
        """True/False for test samples, None when the true label is unknown."""
        if not self.true_label:
            return None
        return self.true_label == self.predicted_label