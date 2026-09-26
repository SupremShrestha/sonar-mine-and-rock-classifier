from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Count
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from .forms import ProfileForm, SignUpForm


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, f"Welcome, {user.username}! Your account has been created.")
            return redirect("home")
    else:
        form = SignUpForm()

    return render(request, "registration/signup.html", {"form": form})


class ProfileView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    form_class = ProfileForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("profile")
    success_message = "Your account has been updated."

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        predictions = self.request.user.predictions.all()
        by_label = {
            row["predicted_label"]: row["total"]
            for row in predictions.values("predicted_label").annotate(total=Count("id"))
        }
        context["total_predictions"] = predictions.count()
        context["mine_count"] = by_label.get("M", 0)
        context["rock_count"] = by_label.get("R", 0)
        context["last_prediction"] = predictions.first()  # Prediction.Meta orders -created_at
        return context


class PasswordChangeView(SuccessMessageMixin, auth_views.PasswordChangeView):
    template_name = "accounts/password_change_form.html"
    success_url = reverse_lazy("home")
    success_message = "Your password has been changed."


class PasswordResetView(SuccessMessageMixin, auth_views.PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("login")
    success_message = (
        "If an account exists for that email, we've sent password reset instructions."
    )


class PasswordResetConfirmView(SuccessMessageMixin, auth_views.PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("login")
    success_message = "Your password has been reset. You can now log in."