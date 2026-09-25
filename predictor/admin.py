from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm
from django.contrib.auth.models import User
from django.db.models import Count

from accounts.forms import UniqueEmailMixin

from .models import Prediction


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = (
        "created_at", "user", "source", "source_name",
        "predicted_label", "confidence_percent", "true_label", "correct",
    )
    list_filter = ("predicted_label", "source", "created_at")
    search_fields = ("user__username", "user__email", "source_name")
    date_hierarchy = "created_at"
    list_select_related = ("user",)
    list_per_page = 50

    # Predictions are records of what happened, so they are view-only.
    readonly_fields = (
        "user", "created_at", "source", "source_name", "predicted_label",
        "confidence", "probability_mine", "true_label", "features",
    )
    fieldsets = (
        (None, {"fields": ("user", "created_at", "source", "source_name")}),
        ("Result", {"fields": ("predicted_label", "confidence", "probability_mine", "true_label")}),
        ("Raw sonar readings", {"fields": ("features",), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description="Confidence", ordering="confidence")
    def confidence_percent(self, obj):
        return f"{obj.confidence:.0%}"

    @admin.display(description="Correct", boolean=True)
    def correct(self, obj):
        return obj.is_correct


class AdminUserAddForm(UniqueEmailMixin, AdminUserCreationForm):
    """New users created in the admin must have a unique email."""
    email = forms.EmailField(required=True)


class AdminUserEditForm(UniqueEmailMixin, UserChangeForm):
    """Existing users may have no email, but it can't clash with another user's."""


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    form = AdminUserEditForm
    add_form = AdminUserAddForm
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "usable_password", "password1", "password2"),
        }),
    )
    list_display = (
        "username", "email", "is_staff", "is_active",
        "date_joined", "last_login", "prediction_count",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups", "date_joined")
    date_hierarchy = "date_joined"

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_prediction_count=Count("predictions"))

    @admin.display(description="Predictions", ordering="_prediction_count")
    def prediction_count(self, obj):
        return obj._prediction_count