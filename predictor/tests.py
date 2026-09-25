import json

from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from . import ml
from .models import Prediction


def sample_row():
    return ml.get_sample_rows()[0]


def to_csv(values):
    return ",".join(str(v) for v in values)


class PredictPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("suprem", "s@example.com", "pw-12345-abc")
        self.client.force_login(self.user)
        self.url = reverse("home")
        self.row = sample_row()
        self.text = to_csv(self.row["features"])

    def test_login_required(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.url), f"{reverse('login')}?next={self.url}")

    def test_page_loads(self):
        self.assertContains(self.client.get(self.url), "Classify a sonar return")

    def test_sample_saves_and_redirects_to_result(self):
        r = self.client.post(self.url, {"use_sample": "1"}, follow=True)
        p = Prediction.objects.get()
        self.assertRedirects(r, reverse("prediction_detail", args=[p.pk]))
        self.assertEqual(p.user, self.user)
        self.assertEqual(p.source, Prediction.Source.SAMPLE)
        self.assertIn(p.true_label, ("M", "R"))
        self.assertIsNotNone(p.is_correct)
        self.assertContains(r, "Held-out test row #")
        self.assertContains(r, "True label")

    def test_pasted_values_saved(self):
        r = self.client.post(self.url, {"pasted_values": self.text}, follow=True)
        p = Prediction.objects.get()
        self.assertEqual(p.source, Prediction.Source.PASTED)
        self.assertEqual(len(p.features), 60)
        self.assertEqual(p.true_label, "")
        self.assertIsNone(p.is_correct)
        self.assertContains(r, "Pasted values")

    def test_label_column_and_whitespace_accepted(self):
        self.client.post(self.url, {"pasted_values": self.text.replace(",", "\n") + "\nR"})
        self.assertEqual(Prediction.objects.count(), 1)

    def test_csv_upload_shows_file_name_on_result(self):
        f = SimpleUploadedFile("my_reading.csv", self.text.encode())
        r = self.client.post(self.url, {"csv_file": f}, follow=True)
        self.assertContains(r, "my_reading.csv")
        self.assertEqual(Prediction.objects.get().source, Prediction.Source.CSV)

    def test_csv_with_header(self):
        header = ",".join(f"freq_{i}" for i in range(1, 61))
        f = SimpleUploadedFile("row.csv", f"{header}\n{self.text}\n".encode())
        self.client.post(self.url, {"csv_file": f})
        self.assertEqual(Prediction.objects.count(), 1)

    def test_invalid_input_saves_nothing(self):
        cases = [
            {"pasted_values": "0.1, 0.2, 0.3"},
            {"pasted_values": ",".join(["1.7"] * 60)},
            {"pasted_values": ",".join(["abc"] * 60)},
            {"csv_file": SimpleUploadedFile("row.txt", self.text.encode())},
            {"csv_file": SimpleUploadedFile("row.csv", f"{self.text}\n{self.text}\n{self.text}\n".encode())},
            {},
        ]
        for data in cases:
            r = self.client.post(self.url, data)
            self.assertEqual(r.status_code, 200)
        self.assertEqual(Prediction.objects.count(), 0)

    def test_specific_error_messages(self):
        self.assertContains(self.client.post(self.url, {"pasted_values": "0.1, 0.2"}), "Expected exactly 60")
        both = {"csv_file": SimpleUploadedFile("row.csv", self.text.encode()), "pasted_values": self.text}
        self.assertContains(self.client.post(self.url, both), "not both")
        self.assertContains(self.client.post(self.url, {}), "Upload a CSV file or paste 60 values")

    def test_reloading_result_page_does_not_create_duplicates(self):
        r = self.client.post(self.url, {"pasted_values": self.text})
        for _ in range(3):
            self.client.get(r["Location"])
        self.assertEqual(Prediction.objects.count(), 1)


class OwnershipAndHistoryTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", "a@example.com", "pw-12345-abc")
        self.bob = User.objects.create_user("bob", "b@example.com", "pw-12345-abc")
        row = sample_row()
        self.make = lambda user, n=1: [
            Prediction.objects.create(
                user=user, source="pasted", source_name=f"Pasted values {i}",
                features=row["features"], predicted_label="R", confidence=0.9, probability_mine=0.1,
            ) for i in range(n)
        ]

    def test_other_users_prediction_is_404(self):
        (p,) = self.make(self.bob)
        self.client.force_login(self.alice)
        self.assertEqual(self.client.get(reverse("prediction_detail", args=[p.pk])).status_code, 404)

    def test_owner_can_open_prediction(self):
        (p,) = self.make(self.alice)
        self.client.force_login(self.alice)
        self.assertEqual(self.client.get(reverse("prediction_detail", args=[p.pk])).status_code, 200)

    def test_history_shows_only_own(self):
        self.make(self.alice); self.make(self.bob)
        self.client.force_login(self.alice)
        r = self.client.get(reverse("history"))
        self.assertEqual(len(r.context["page"].object_list), 1)

    def test_history_empty_state(self):
        self.client.force_login(self.alice)
        self.assertContains(self.client.get(reverse("history")), "No predictions yet")

    def test_history_paginates(self):
        self.make(self.alice, 25)
        self.client.force_login(self.alice)
        self.assertEqual(len(self.client.get(reverse("history")).context["page"]), 20)
        self.assertEqual(len(self.client.get(reverse("history") + "?page=2").context["page"]), 5)

    def test_history_requires_login(self):
        self.assertEqual(self.client.get(reverse("history")).status_code, 302)

    def test_deleting_user_deletes_their_predictions(self):
        self.make(self.alice, 2)
        self.alice.delete()
        self.assertEqual(Prediction.objects.count(), 0)


class AdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("root", "root@example.com", "pw-12345-abc")
        self.alice = User.objects.create_user("alice", "a@example.com", "pw-12345-abc")
        row = sample_row()
        self.p = Prediction.objects.create(
            user=self.alice, source="sample", source_name="Held-out test row #9",
            features=row["features"], predicted_label="M", confidence=0.8,
            probability_mine=0.8, true_label="R",
        )
        self.list_url = reverse("admin:predictor_prediction_changelist")

    def test_anonymous_is_sent_to_admin_login(self):
        self.assertEqual(self.client.get(self.list_url).status_code, 302)

    def test_regular_user_is_blocked(self):
        self.client.force_login(self.alice)
        self.assertEqual(self.client.get(self.list_url).status_code, 302)

    def test_superuser_sees_predictions_with_search_and_filters(self):
        self.client.force_login(self.admin)
        r = self.client.get(self.list_url)
        self.assertContains(r, "alice")
        self.assertContains(r, "80%")
        self.assertEqual(self.client.get(self.list_url + "?q=alice").context["cl"].result_count, 1)
        self.assertEqual(self.client.get(self.list_url + "?q=nobody").context["cl"].result_count, 0)
        self.assertEqual(self.client.get(self.list_url + "?predicted_label__exact=R").context["cl"].result_count, 0)

    def test_predictions_are_view_only(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("admin:predictor_prediction_add")).status_code, 403)
        r = self.client.get(reverse("admin:predictor_prediction_change", args=[self.p.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'name="confidence"')

    def test_staff_with_view_permission_only(self):
        staff = User.objects.create_user("staff", "st@example.com", "pw-12345-abc", is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(self.list_url).status_code, 403)
        staff.user_permissions.add(Permission.objects.get(codename="view_prediction"))
        staff = User.objects.get(pk=staff.pk)
        self.client.force_login(staff)
        self.assertEqual(self.client.get(self.list_url).status_code, 200)
        self.assertEqual(self.client.post(reverse("admin:predictor_prediction_delete", args=[self.p.pk]), {"post": "yes"}).status_code, 403)

    def test_user_list_shows_prediction_count(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse("admin:auth_user_changelist"))
        self.assertContains(r, "Predictions")
        counts = {u.username: u._prediction_count for u in r.context["cl"].result_list}
        self.assertEqual(counts["alice"], 1)
        self.assertEqual(counts["root"], 0)


class ModelTests(TestCase):
    def test_accuracy_on_held_out_rows(self):
        rows = ml.get_sample_rows()
        correct = sum(ml.predict(r["features"])["predicted_label"] == r["true_label"] for r in rows)
        self.assertGreaterEqual(correct / len(rows), 0.85)
