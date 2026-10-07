from django.conf import settings
from django.test import TestCase

class ServerBoundaryTests(TestCase):
    def test_public_role_has_no_authentication_or_private_routes(self):
        if settings.SERVER_ROLE != "public":
            self.skipTest("Separate public-role process required")
        self.assertContains(self.client.get("/"), "Noch keine Veröffentlichungen")
        for path in ["/anmelden/", "/anmelden/code/", "/kontext/", "/organisationen/neu/", "/benutzer/", "/einladung/", "/einladung/annehmen/", "/sitzungen/", "/vorlagen/", "/stammdaten/"]:
            self.assertEqual(self.client.get(path).status_code, 404)

    def test_protected_role_has_no_internal_administration_route(self):
        if settings.SERVER_ROLE != "protected":
            self.skipTest("Separate protected-role process required")
        self.assertEqual(self.client.get("/organisationen/neu/").status_code, 404)
        self.assertEqual(self.client.get("/benutzer/").status_code, 404)
        self.assertEqual(self.client.get("/einladung/").status_code, 404)
        self.assertEqual(self.client.get("/sitzungen/neu/").status_code, 404)
        self.assertEqual(self.client.get("/stammdaten/").status_code, 404)
        self.assertEqual(self.client.get("/vorlagen/neu/").status_code, 404)
        self.assertContains(self.client.get("/anmelden/"), "Willkommen zurück")

    def test_role_specific_cookies(self):
        self.assertEqual(settings.SESSION_COOKIE_NAME, f"bm_{settings.SERVER_ROLE}_session")
        self.assertEqual(settings.CSRF_COOKIE_NAME, f"bm_{settings.SERVER_ROLE}_csrf")
