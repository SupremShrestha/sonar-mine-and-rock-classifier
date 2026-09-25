from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

VALID = {
    "username": "suprem",
    "email": "s@example.com",
    "password1": "Str0ng-pass-987",
    "password2": "Str0ng-pass-987",
}


class SignupTests(TestCase):
    def test_signup_creates_user_and_logs_in(self):
        r = self.client.post(reverse("signup"), VALID, follow=True)
        self.assertRedirects(r, reverse("home"))
        self.assertTrue(User.objects.filter(username="suprem").exists())
        self.assertTrue(r.context["user"].is_authenticated)
        self.assertContains(r, "Welcome, suprem")

    def test_duplicate_email_rejected_case_insensitively(self):
        User.objects.create_user("a", "S@Example.com", "x")
        r = self.client.post(reverse("signup"), {**VALID, "username": "b"})
        self.assertContains(r, "already exists")
        self.assertFalse(User.objects.filter(username="b").exists())

    def test_weak_password_rejected(self):
        r = self.client.post(reverse("signup"), {**VALID, "password1": "12345678", "password2": "12345678"})
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_logged_in_user_is_redirected_away(self):
        self.client.force_login(User.objects.create_user("a", "a@x.com", "pw"))
        self.assertRedirects(self.client.get(reverse("signup")), reverse("home"))


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("suprem", "s@example.com", "Str0ng-pass-987")

    def test_home_requires_login(self):
        r = self.client.get(reverse("home"))
        self.assertRedirects(r, f"{reverse('login')}?next={reverse('home')}")

    def test_login_success(self):
        r = self.client.post(reverse("login"), {"username": "suprem", "password": "Str0ng-pass-987"}, follow=True)
        self.assertRedirects(r, reverse("home"))

    def test_login_wrong_password(self):
        r = self.client.post(reverse("login"), {"username": "suprem", "password": "nope"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "correct username and password")

    def test_login_honours_next(self):
        r = self.client.post(reverse("login") + "?next=/admin/", {"username": "suprem", "password": "Str0ng-pass-987", "next": "/admin/"})
        self.assertEqual(r["Location"], "/admin/")

    def test_logout_via_post(self):
        self.client.force_login(self.user)
        r = self.client.post(reverse("logout"), follow=True)
        self.assertRedirects(r, reverse("login"))
        self.assertFalse(r.context["user"].is_authenticated)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)


import re

from django.core import mail


class PasswordChangeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("suprem", "s@example.com", "Old-pass-12345")

    def test_requires_login(self):
        r = self.client.get(reverse("password_change"))
        self.assertRedirects(r, f"{reverse('login')}?next={reverse('password_change')}")

    def test_wrong_old_password(self):
        self.client.force_login(self.user)
        r = self.client.post(reverse("password_change"), {
            "old_password": "wrong", "new_password1": "New-pass-98765", "new_password2": "New-pass-98765"})
        self.assertEqual(r.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Old-pass-12345"))

    def test_success_keeps_user_logged_in(self):
        self.client.force_login(self.user)
        r = self.client.post(reverse("password_change"), {
            "old_password": "Old-pass-12345", "new_password1": "New-pass-98765", "new_password2": "New-pass-98765"},
            follow=True)
        self.assertRedirects(r, reverse("home"))
        self.assertContains(r, "Your password has been changed.")
        self.assertTrue(r.context["user"].is_authenticated)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("New-pass-98765"))


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("suprem", "s@example.com", "Old-pass-12345")

    def test_full_reset_flow(self):
        r = self.client.post(reverse("password_reset"), {"email": "s@example.com"}, follow=True)
        self.assertRedirects(r, reverse("login"))
        self.assertContains(r, "sent password reset instructions")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, "Reset your Sonar Classifier password")
        link = re.search(r"http://testserver(/accounts/reset/\S+)", mail.outbox[0].body).group(1)

        r = self.client.get(link)
        self.assertEqual(r.status_code, 302)
        r = self.client.post(r["Location"], {"new_password1": "New-pass-98765", "new_password2": "New-pass-98765"}, follow=True)
        self.assertRedirects(r, reverse("login"))
        self.assertContains(r, "Your password has been reset")
        # Log in through the real login view (axes needs the request object,
        # so the test client's shortcut client.login() can't be used).
        r = self.client.post(reverse("login"), {"username": "suprem", "password": "New-pass-98765"})
        self.assertRedirects(r, reverse("home"), fetch_redirect_response=False)

    def test_unknown_email_gets_same_response_but_no_mail(self):
        r = self.client.post(reverse("password_reset"), {"email": "nobody@example.com"}, follow=True)
        self.assertContains(r, "sent password reset instructions")
        self.assertEqual(len(mail.outbox), 0)

    def test_invalid_link(self):
        r = self.client.get(reverse("password_reset_confirm", args=["bad", "token"]), follow=True)
        self.assertContains(r, "invalid or has already been used")

    def test_link_cannot_be_reused(self):
        self.client.post(reverse("password_reset"), {"email": "s@example.com"})
        link = re.search(r"http://testserver(/accounts/reset/\S+)", mail.outbox[0].body).group(1)
        r = self.client.get(link)
        self.client.post(r["Location"], {"new_password1": "New-pass-98765", "new_password2": "New-pass-98765"})
        fresh = self.client.__class__()
        r = fresh.get(link, follow=True)
        self.assertContains(r, "invalid or has already been used")


class LoginPageTests(TestCase):
    def test_forgot_password_link_present(self):
        self.assertContains(self.client.get(reverse("login")), reverse("password_reset"))

    def test_authenticated_user_skips_login_page(self):
        self.client.force_login(User.objects.create_user("a", "a@x.com", "pw"))
        self.assertRedirects(self.client.get(reverse("login")), reverse("home"))


from datetime import timedelta

from axes.models import AccessAttempt
from django.utils import timezone


class LoginLockoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("suprem", "s@example.com", "Str0ng-pass-987")
        self.other = User.objects.create_user("other", "o@example.com", "Str0ng-pass-987")
        self.login_url = reverse("login")

    def fail(self, username="suprem", times=1, url=None):
        for _ in range(times):
            self.client.post(url or self.login_url, {"username": username, "password": "wrong"})

    def good_login(self, username="suprem", url=None):
        return self.client.post(url or self.login_url, {"username": username, "password": "Str0ng-pass-987"})

    def test_locked_after_five_failures_even_with_right_password(self):
        self.fail(times=5)
        r = self.good_login()
        self.assertEqual(r.status_code, 429)
        self.assertContains(r, "Login temporarily blocked", status_code=429)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_four_failures_do_not_lock(self):
        self.fail(times=4)
        self.assertEqual(self.good_login().status_code, 302)

    def test_lock_is_per_username(self):
        self.fail(times=5)
        self.assertEqual(self.good_login("other").status_code, 302)

    def test_success_resets_the_counter(self):
        self.fail(times=4)
        self.good_login()
        self.client.post(reverse("logout"))
        self.fail(times=4)
        self.assertEqual(self.good_login().status_code, 302)

    def test_lock_expires_after_cooloff(self):
        self.fail(times=5)
        self.assertEqual(self.good_login().status_code, 429)
        AccessAttempt.objects.update(attempt_time=timezone.now() - timedelta(minutes=16))
        self.assertEqual(self.good_login().status_code, 302)

    def test_lockout_page_links_to_password_reset(self):
        self.fail(times=5)
        self.assertContains(self.good_login(), reverse("password_reset"), status_code=429)

    def test_admin_login_is_protected_too(self):
        admin = User.objects.create_superuser("root", "r@example.com", "Str0ng-pass-987")
        url = reverse("admin:login")
        for _ in range(5):
            self.client.post(url, {"username": "root", "password": "wrong", "next": "/admin/"})
        r = self.client.post(url, {"username": "root", "password": "Str0ng-pass-987", "next": "/admin/"})
        self.assertEqual(r.status_code, 429)


class AdminUserEmailTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("root", "root@example.com", "Str0ng-pass-987")
        self.alice = User.objects.create_user("alice", "Alice@Example.com", "Str0ng-pass-987")
        self.client.force_login(self.admin)
        self.add_url = reverse("admin:auth_user_add")

    def add_data(self, **overrides):
        data = {
            "username": "newbie",
            "email": "newbie@example.com",
            "usable_password": "true",
            "password1": "Str0ng-pass-987",
            "password2": "Str0ng-pass-987",
        }
        data.update(overrides)
        return data

    def edit_data(self, user, **overrides):
        data = {
            "username": user.username,
            "email": user.email,
            "first_name": "",
            "last_name": "",
            "is_active": "on",
            "date_joined_0": user.date_joined.strftime("%Y-%m-%d"),
            "date_joined_1": user.date_joined.strftime("%H:%M:%S"),
        }
        data.update(overrides)
        return data

    def edit_url(self, user):
        return reverse("admin:auth_user_change", args=[user.pk])

    def test_add_user_with_new_email(self):
        r = self.client.post(self.add_url, self.add_data())
        self.assertEqual(r.status_code, 302)
        self.assertTrue(User.objects.filter(username="newbie", email="newbie@example.com").exists())

    def test_add_user_with_duplicate_email_is_rejected_case_insensitively(self):
        r = self.client.post(self.add_url, self.add_data(email="alice@example.com"))
        self.assertContains(r, "An account with this email already exists.")
        self.assertFalse(User.objects.filter(username="newbie").exists())

    def test_add_user_requires_email(self):
        r = self.client.post(self.add_url, self.add_data(email=""))
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="newbie").exists())

    def test_editing_a_user_keeps_their_own_email_valid(self):
        r = self.client.post(self.edit_url(self.alice), self.edit_data(self.alice, first_name="Alice"))
        self.assertEqual(r.status_code, 302)
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.first_name, "Alice")

    def test_cannot_change_email_to_another_users_email(self):
        original = self.alice.email
        r = self.client.post(self.edit_url(self.alice), self.edit_data(self.alice, email="ROOT@example.com"))
        self.assertContains(r, "An account with this email already exists.")
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.email, original)

    def test_existing_user_without_email_can_still_be_edited(self):
        bare = User.objects.create_user("bare", "", "Str0ng-pass-987")
        r = self.client.post(self.edit_url(bare), self.edit_data(bare, first_name="Bare"))
        self.assertEqual(r.status_code, 302)
