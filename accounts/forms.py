from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()


class UniqueEmailMixin:
    """Reject an email that another account already uses (case-insensitive).

    A blank email is allowed here; make the field required on the form if
    you need one. Used by both the signup form and the admin user forms.
    """

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip()
        if email:
            others = User.objects.filter(email__iexact=email)
            if self.instance.pk:
                others = others.exclude(pk=self.instance.pk)
            if others.exists():
                raise forms.ValidationError("An account with this email already exists.")
        return email


class SignUpForm(UniqueEmailMixin, UserCreationForm):
    email = forms.EmailField(
        required=True,
        help_text="Used for password resets.",
    )

    class Meta(UserCreationForm.Meta):
        fields = ("username", "email")