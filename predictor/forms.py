import csv
import io
import re

from django import forms

from .ml import N_FEATURES, validate_feature_row
from .models import Prediction

MAX_UPLOAD_BYTES = 100 * 1024  # plenty for one 60-value row


def _strip_label_column(values):
    """A row copied from the original sonar dataset has 61 values (the last is
    the M/R label). Drop it so those rows work too."""
    if len(values) == N_FEATURES + 1:
        return values[:N_FEATURES]
    return values


def _row_from_csv(uploaded_file):
    if not uploaded_file.name.lower().endswith(".csv"):
        raise ValueError("Please upload a .csv file.")
    if uploaded_file.size > MAX_UPLOAD_BYTES:
        raise ValueError("File is too large for a single 60-value row.")

    try:
        text = uploaded_file.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("Could not read the file as UTF-8 text.")

    rows = [row for row in csv.reader(io.StringIO(text)) if row]
    if not rows:
        raise ValueError("The CSV file is empty.")
    if len(rows) > 2:
        raise ValueError(
            f"Expected one data row (optionally with a header row above it), found {len(rows)} rows."
        )
    # One row = data only; two rows = header + data.
    return [v.strip() for v in rows[-1]]


def _row_from_text(text):
    return [v for v in re.split(r"[,\s]+", text.strip()) if v]


class SonarInputForm(forms.Form):
    csv_file = forms.FileField(
        required=False,
        label="Upload a CSV file",
        help_text="One row of 60 values between 0 and 1. A header row is optional.",
    )
    pasted_values = forms.CharField(
        required=False,
        label="Or paste the 60 values",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "0.0200, 0.0371, 0.0428, ..."}),
        help_text="Separated by commas, spaces or new lines.",
    )

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned

        csv_file = cleaned.get("csv_file")
        pasted = (cleaned.get("pasted_values") or "").strip()

        if csv_file and pasted:
            self.add_error(None, "Use either a CSV file or pasted values, not both.")
            return cleaned
        if not csv_file and not pasted:
            self.add_error(None, "Upload a CSV file or paste 60 values.")
            return cleaned

        try:
            raw = _row_from_csv(csv_file) if csv_file else _row_from_text(pasted)
            features, error = validate_feature_row(_strip_label_column(raw))
            if error:
                raise ValueError(error)
        except ValueError as exc:
            self.add_error("csv_file" if csv_file else "pasted_values", str(exc))
            return cleaned

        cleaned["features"] = features
        if csv_file:
            cleaned["source"] = Prediction.Source.CSV
            cleaned["source_name"] = csv_file.name
        else:
            cleaned["source"] = Prediction.Source.PASTED
            cleaned["source_name"] = "Pasted values"
        return cleaned