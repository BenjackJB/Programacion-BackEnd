from django.test import TestCase
from django.urls import reverse


class SeparateLayersURLTests(TestCase):
    def test_admin_home_requires_login(self):
        url = reverse('admin_home')
        self.assertEqual(url, '/admin/')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_admin_programmer_requires_login(self):
        url = reverse('programmers_table')
        self.assertEqual(url, '/admin/programmer/')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response.url)

    def test_api_programmer_requires_authentication(self):
        url = reverse('programmer-list')
        self.assertEqual(url, '/api/programmer/')

        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
