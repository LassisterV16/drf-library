from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework import status

from rest_framework.test import APIClient

from books.models import Book
from books.serializers import BookSerializer

BOOKS_URL = reverse("books:book-list")


def detail_url(book_id):
    return reverse("books:book-detail", args=[book_id])


class BookPermissionsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.book = Book.objects.create(
            title="Wild at Heart",
            author="John Eldredge",
            cover="HARD",
            inventory=15,
            daily_fee=1.25,
        )

    def test_unauthenticated_list_books_allowed(self):
        books = Book.objects.all()
        serializer = BookSerializer(books, many=True)
        res = self.client.get(BOOKS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_unauthenticated_create_books_forbidden(self):
        res = self.client.post(BOOKS_URL, {})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_delete_books_forbidden(self):
        auth_user = get_user_model().objects.create_user("user@example.com", "password")
        self.client.force_authenticate(auth_user)

        url = detail_url(self.book.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_create_books_allowed(self):
        admin_user = get_user_model().objects.create_superuser(
            "admin@admin.com", "adminpassword"
        )
        self.client.force_authenticate(admin_user)

        payload = {
            "title": "Atomic Habits",
            "author": "James Clear",
            "cover": "SOFT",
            "inventory": 16,
            "daily_fee": 0.89,
        }
        res = self.client.post(BOOKS_URL, payload)
        book = Book.objects.get(id=res.data["id"])
        serializer = BookSerializer(book)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, serializer.data)
