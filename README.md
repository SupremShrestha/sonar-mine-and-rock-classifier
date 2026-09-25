# Sonar Target Classifier

A Django web app that classifies sonar returns as **Mine** or **Rock** using a
trained SVM (RBF kernel) on the classic UCI Sonar dataset (60 frequency-band
energy readings per return). The saved model scores 88.1% (37/42) on its
held-out test rows.

## Features

- Sign up, log in and log out with Django's built-in authentication
- Password change (logged in) and password reset by email
- Classify a sonar return by uploading a one-row CSV, pasting 60 values, or
  running a random held-out test sample (the true label is shown afterwards)
- Every prediction is saved to the user's account, with a paginated history page
- Django admin for managing users, groups and permissions, and for browsing
  predictions (search, filters, date drill-down; predictions are view-only)

## Setup

Requires Python 3.12 or newer.

```bash
git clone <your-repo-url> sonar
cd sonar
python -m venv .venv

# activate the virtual environment
source .venv/bin/activate          # bash / zsh
source .venv/bin/activate.fish     # fish
# .venv\Scripts\Activate.ps1       # Windows PowerShell

pip install -r requirements.txt
cp .env.example .env               # optional for local development
python manage.py migrate
python manage.py createsuperuser
python manage.py check_model       # should print: 37/42 correct (88.1%)
python manage.py runserver
```

Open http://127.0.0.1:8000/. The admin is at http://127.0.0.1:8000/admin/.

## Configuration

Settings are read from environment variables, or from a `.env` file in the
project root. Defaults are set up for local development.

| Variable | Purpose | Default |
|---|---|---|
| `DJANGO_DEBUG` | Debug mode. Set to `False` on a real server. | `True` |
| `DJANGO_SECRET_KEY` | Signing key. **Required** when debug is off. | insecure dev key |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hostnames served. | empty (localhost only in debug) |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Comma-separated origins with scheme. | empty |
| `DJANGO_BEHIND_PROXY` | Trust `X-Forwarded-Proto` from a reverse proxy. | off |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | SMTP login (Gmail). If unset, emails print in the terminal. | unset |

Generate a secret key:

```bash
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
```

## Project structure

```
sonar/
├── manage.py
├── sonarsite/            project settings and root URLs
├── accounts/             signup, login/logout, password change and reset
├── predictor/            the classifier
│   ├── ml.py             loads the model once; predict() and input validation
│   ├── ml_models/        trained model, scaler, label encoder, held-out samples
│   ├── models.py         Prediction (saved per user)
│   ├── forms.py          CSV upload / pasted-values form
│   ├── views.py          predict, result and history pages
│   ├── admin.py          Prediction and User admin
│   └── management/commands/check_model.py
├── templates/            base layout, partials, accounts/ and predictor/ pages
└── static/style.css
```

## Tests

```bash
python manage.py test
```

42 tests cover signup, login/logout, password change and reset, input
validation, saving predictions, privacy between users, pagination and the
admin permissions.

## Users, staff and permissions

| Kind of user | Can enter `/admin/`? | What they can do |
|---|---|---|
| Regular user | No | Use the app and see their own history |
| Staff user | Yes | Only what their permissions or groups allow |
| Superuser | Yes | Everything |

To give someone read-only access to predictions: create a group with the
permission `predictor | prediction | Can view prediction`, then tick
**Staff status** on the user and add them to the group.

## About the model

The model files in `predictor/ml_models/` were saved with scikit-learn 1.6.1.
Newer versions print a warning when loading them, which the app silences after
checking the accuracy is unchanged. After upgrading scikit-learn, run
`python manage.py check_model` to confirm it still scores about 88%.

## Deploying

1. Set `DJANGO_DEBUG=False`, `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` and
   `DJANGO_CSRF_TRUSTED_ORIGINS`, plus real email credentials. Django refuses
   to pass its deployment check with the terminal email backend.
2. Set `DJANGO_BEHIND_PROXY=True` if your host terminates HTTPS in a proxy.
3. Run `python manage.py migrate` and `python manage.py collectstatic`.
4. Serve with a production server (for example gunicorn) and serve `staticfiles/`
   with your host or a package such as WhiteNoise. Django's `runserver` is for
   development only.
5. Verify: `python manage.py check --deploy`.

## Known limitations and ideas

- Login attempts are not rate limited. Consider `django-axes` before exposing
  the site publicly.
- Email uniqueness is enforced at signup, but users created in the admin can
  share an email address.
- The model can be retrained from the original Sonar CSV with a training
  script to remove the scikit-learn version warning entirely.
