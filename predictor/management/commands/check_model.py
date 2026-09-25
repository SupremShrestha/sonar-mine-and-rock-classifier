from django.core.management.base import BaseCommand, CommandError

from predictor import ml


class Command(BaseCommand):
    help = "Score the saved model on its held-out sample rows to confirm it loads and predicts correctly."

    def handle(self, *args, **options):
        rows = ml.get_sample_rows()
        correct = sum(
            ml.predict(row["features"])["predicted_label"] == row["true_label"]
            for row in rows
        )
        accuracy = correct / len(rows)
        self.stdout.write(f"{correct}/{len(rows)} correct ({accuracy:.1%})")

        if accuracy < 0.85:
            raise CommandError("Accuracy is lower than expected (about 88%). The model files may be damaged or incompatible.")
        self.stdout.write(self.style.SUCCESS("Model OK"))