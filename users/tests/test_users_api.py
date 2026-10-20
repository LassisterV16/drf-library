from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from users.serializers import UserSerializer

MANAGE_URL = reverse("users:manage")


class UserAccountTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("user@example.com", "password")
        self.client.force_authenticate(self.user)

    def test_user_registration_successful_with_hash_password(self):
        url = reverse("users:register")
        payload = {
            "email": "user@email.com",
            "first_name": "Firstname",
            "last_name": "Lastname",
            "password": "userpassword",
        }

        res = self.client.post(url, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        user = get_user_model().objects.get(id=res.data["id"])
        self.assertTrue(user.check_password(payload["password"]))

    def test_get_jwt_token_successful(self):
        url = reverse("users:token_obtain_pair")
        payload = {"email": "user@example.com", "password": "password"}
        res = self.client.post(url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("refresh", res.data)
        self.assertIn("access", res.data)

    def test_user_get_profile_allowed(self):
        res = self.client.get(MANAGE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        serializer = UserSerializer(self.user)
        self.assertEqual(res.data, serializer.data)

    def test_user_patch_profile_allowed(self):
        payload = {
            "first_name": "First",
            "last_name": "Last",
        }
        res = self.client.patch(MANAGE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        serializer = UserSerializer(self.user)
        self.assertEqual(res.data, serializer.data)
