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


class ProfileForm(UniqueEmailMixin, forms.ModelForm):
    """Lets a signed-in user update their display name and email.

    Username is intentionally left out — it's the login identifier and
    changing it would need its own confirmation flow, so that stays on
    the account page as a read-only field instead.
    """

    first_name = forms.CharField(
        required=True,
        label="Full name",
        max_length=150,
    )
    email = forms.EmailField(
        required=True,
        help_text="Used for password resets and login notices.",
    )

    class Meta:
        model = User
        fields = ("first_name", "email")