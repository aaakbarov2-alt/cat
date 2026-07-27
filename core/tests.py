from django.contrib.auth.models import User
from django.test import TestCase
from django.test import override_settings
from django.core import mail


class PublicNavigationTests(TestCase):
    def test_public_navigation_has_working_destinations_and_mobile_bundle(self):
        response = self.client.get("/")

        self.assertContains(response, 'href="/#about"')
        self.assertContains(response, 'href="/exams/"')
        self.assertContains(response, 'href="/accounts/login/"')
        self.assertContains(response, 'href="/accounts/signup/"')
        self.assertContains(response, "bootstrap.bundle.min.js")
        self.assertContains(response, 'id="mainNavigation"')
        self.assertContains(response, "footer.css?v=20260717.2")
        self.assertNotContains(response, 'href="#"')

    def test_authenticated_navigation_shows_dashboard_and_logout(self):
        user = User.objects.create_user(username="nav-user", password="test-pass-123")
        self.client.force_login(user)

        response = self.client.get("/")

        self.assertContains(response, 'href="/accounts/dashboard/"')
        self.assertContains(response, 'href="/accounts/logout/"')
        self.assertNotContains(response, 'href="/accounts/login/"')

    def test_admin_dashboard_uses_real_unfold_dashboard_shell(self):
        admin_user = User.objects.create_superuser(
            username="dashboard-admin",
            email="dashboard@example.com",
            password="test-pass-123",
        )
        self.client.force_login(admin_user)

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Activity overview")
        self.assertContains(response, "Published tests")
        self.assertContains(response, "No activity yet")
        self.assertContains(response, "/static/unfold/css/styles.css")

    def test_navigation_marks_only_the_current_main_page_active(self):
        home_response = self.client.get("/")
        self.assertContains(home_response, 'class="nav-link active" href="/"')

        user = User.objects.create_user(username="exam-nav", password="test-pass-123")
        self.client.force_login(user)
        exams_response = self.client.get("/exams/")
        self.assertContains(exams_response, 'class="nav-link active" href="/exams/"')
        self.assertNotContains(exams_response, 'class="nav-link active" href="/"')

    def test_public_information_pages_resolve(self):
        faq_response = self.client.get("/faq/")
        privacy_response = self.client.get("/privacy/")
        terms_response = self.client.get("/terms/")

        self.assertEqual(faq_response.status_code, 200)
        self.assertContains(faq_response, "Frequently Asked Questions")
        self.assertEqual(privacy_response.status_code, 200)
        self.assertContains(privacy_response, "Privacy Policy")
        self.assertEqual(terms_response.status_code, 200)
        self.assertContains(terms_response, "Terms of Use")
        self.assertContains(terms_response, "not an official IELTS examination service")

    def test_footer_uses_configured_links_without_fake_social_destinations(self):
        response = self.client.get("/")

        self.assertContains(response, "&copy;", html=False)
        self.assertContains(response, "support@ieltsmock.com")
        self.assertNotContains(response, "https://www.facebook.com/")
        self.assertNotContains(response, "https://www.instagram.com/")

    def test_account_pages_use_ielts_mock_branding(self):
        login_response = self.client.get("/accounts/login/")
        signup_response = self.client.get("/accounts/signup/")
        reset_response = self.client.get("/accounts/password/reset/")

        self.assertContains(login_response, "Welcome back")
        self.assertNotContains(login_response, "SpcHub")
        self.assertContains(signup_response, "Create your account")
        self.assertContains(reset_response, "Reset your password")

    def test_account_recovery_confirmation_screen_is_branded(self):
        response = self.client.post(
            "/accounts/password/reset/",
            {"email": "missing@example.com"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Check your email")
        self.assertContains(response, "IELTS Mock")

    def test_health_endpoint_reports_database_readiness(self):
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "database": "ok"})

    def test_missing_page_uses_branded_error_template(self):
        response = self.client.get("/this-page-does-not-exist/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Page not found", status_code=404)

    def test_home_has_search_and_accessibility_metadata(self):
        response = self.client.get("/")

        self.assertContains(response, 'rel="canonical"')
        self.assertContains(response, 'property="og:title"')
        self.assertContains(response, 'href="/static/images/favicon.svg"')
        self.assertContains(response, "Skip to main content")
        self.assertContains(response, 'id="main-content"')

    def test_robots_and_sitemap_resolve(self):
        robots_response = self.client.get("/robots.txt")
        sitemap_response = self.client.get("/sitemap.xml")

        self.assertEqual(robots_response.status_code, 200)
        self.assertContains(robots_response, "Disallow: /admin/")
        self.assertContains(robots_response, "/sitemap.xml")
        self.assertEqual(sitemap_response.status_code, 200)
        self.assertEqual(sitemap_response["Content-Type"], "application/xml")
        self.assertContains(sitemap_response, "/faq/")
        self.assertContains(sitemap_response, "/terms/")

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        SUPPORT_EMAIL="support@example.com",
    )
    def test_contact_form_sends_support_email(self):
        response = self.client.post(
            "/contact/",
            {
                "name": "Test Student",
                "email": "student@example.com",
                "subject": "Account help",
                "message": "Please help with my account.",
                "website": "",
            },
        )

        self.assertRedirects(response, "/contact/")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["support@example.com"])
        self.assertEqual(mail.outbox[0].reply_to, ["student@example.com"])
