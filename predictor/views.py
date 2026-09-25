import random

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from . import ml
from .forms import SonarInputForm
from .models import Prediction


def _save_prediction(user, features, source, source_name, true_label=""):
    result = ml.predict(features)
    return Prediction.objects.create(
        user=user,
        source=source,
        source_name=source_name,
        features=features,
        predicted_label=result["predicted_label"],
        confidence=result["confidence"],
        probability_mine=result["class_probabilities"]["M"],
        true_label=true_label,
    )


@login_required
def predict_view(request):
    if request.method == "POST":
        if "use_sample" in request.POST:
            # A random held-out test row, sent through the same code path as user data.
            sample = random.choice(ml.get_sample_rows())
            prediction = _save_prediction(
                request.user,
                sample["features"],
                source=Prediction.Source.SAMPLE,
                source_name=f"Held-out test row #{sample['row_id']}",
                true_label=sample["true_label"],
            )
            return redirect("prediction_detail", pk=prediction.pk)

        form = SonarInputForm(request.POST, request.FILES)
        if form.is_valid():
            prediction = _save_prediction(
                request.user,
                form.cleaned_data["features"],
                source=form.cleaned_data["source"],
                source_name=form.cleaned_data["source_name"],
            )
            # Redirect after POST: reloading the result page can't re-submit the form.
            return redirect("prediction_detail", pk=prediction.pk)
    else:
        form = SonarInputForm()

    return render(request, "predictor/predict.html", {"form": form})


@login_required
def prediction_detail(request, pk):
    # Filtering by user means other people's predictions return a 404.
    prediction = get_object_or_404(Prediction, pk=pk, user=request.user)
    return render(request, "predictor/predict.html", {
        "form": SonarInputForm(),
        "prediction": prediction,
    })


@login_required
def history_view(request):
    paginator = Paginator(request.user.predictions.all(), 20)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "predictor/history.html", {"page": page})