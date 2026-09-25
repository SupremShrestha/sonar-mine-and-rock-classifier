from django.apps import AppConfig


class PredictorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'predictor'

    def ready(self):
        # Load the model once when the server starts, not on every request.
        from . import ml
        ml.load_artifacts()