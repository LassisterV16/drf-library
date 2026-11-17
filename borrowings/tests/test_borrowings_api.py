from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from books.models import Book
from borrowings.models import Borrowing
from borrowings.serializers import BorrowingSerializer, BorrowingListSerializer

BORROWING_URL = reverse("borrowings:borrowing-list")


def return_borrowing_url(borrowing_id):
    return reverse("borrowings:borrowing-return-borrowing", args=[borrowing_id])


def sample_book(**params):
    title = "Atomic Habits"
    author = "James Clear"
    cover = "SOFT"
    inventory = 16
    daily_fee = 0.89

    defaults = {
        "title": title,
        "author": author,
        "cover": cover,
        "inventory": inventory,
        "daily_fee": daily_fee,
    }
    defaults.update(params)

    return Book.objects.create(**defaults)


class UnauthenticatedApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_unauthenticated_list_borrowings_forbidden(self):
        res = self.client.get(BORROWING_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedApiTests(TestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user("user_example.com", "password")
        self.book = sample_book()

        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_authenticated_create_borrowings_allowed(self):
        payload = {
            "expected_return_date": "2026-12-01T13:00:00Z",
            "book": self.book.id,
        }
        book_inventory = self.book.inventory
        res = self.client.post(BORROWING_URL, payload)
        borrowing = Borrowing.objects.get(id=res.data["id"])
        serializer = BorrowingSerializer(borrowing)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data, serializer.data)
        self.assertEqual(res.data["user"], self.user.id)

        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, book_inventory - 1)

    def test_create_borrowing_with_book_inventory_0_not_allowed(self):
        book = sample_book(inventory=0)
        payload = {
            "expected_return_date": "2026-12-01T13:00:00Z",
            "book": book.id,
        }
        res = self.client.post(BORROWING_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        book.refresh_from_db()
        self.assertEqual(book.inventory, 0)

    def test_non_admin_can_see_only_their_own_borrowings(self):
        user_2 = get_user_model().objects.create_user("user2@example.com", "password")
        borrowing_1 = Borrowing.objects.create(
            borrow_date=timezone.now(),
            expected_return_date="2026-12-01T13:00:00Z",
            book=self.book,
            user=self.user,
        )
        Borrowing.objects.create(
            borrow_date=timezone.now(),
            expected_return_date="2026-12-01T13:00:00Z",
            book=self.book,
            user=user_2,
        )
        serializer = BorrowingListSerializer(borrowing_1)
        res = self.client.get(BORROWING_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0], serializer.data)

    def test_successful_return_borrowing(self):
        borrowing = Borrowing.objects.create(
            borrow_date=timezone.now(),
            expected_return_date="2026-12-01T13:00:00Z",
            book=self.book,
            user=self.user,
        )
        book_inventory = self.book.inventory
        url = return_borrowing_url(borrowing.id)
        res = self.client.post(url)

        borrowing.refresh_from_db()
        self.book.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotEqual(borrowing.actual_return_date, None)
        self.assertEqual(self.book.inventory, book_inventory + 1)

    def test_not_allowed_return_returned_borrowing(self):
        borrowing = Borrowing.objects.create(
            borrow_date=timezone.now(),
            expected_return_date="2026-12-01T13:00:00Z",
            actual_return_date="2026-12-01T13:00:00Z",
            book=self.book,
            user=self.user,
        )
        book_inventory = self.book.inventory
        url = return_borrowing_url(borrowing.id)
        res = self.client.post(url)

        self.book.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.book.inventory, book_inventory)


class AdminApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.admin = get_user_model().objects.create_superuser(
            "admin@example.com", "password"
        )
        self.client.force_authenticate(self.admin)

        self.book = sample_book()
        self.user = get_user_model().objects.create_user("user@example.com", "password")
        payload = [
            {
                "borrow_date": timezone.now(),
                "expected_return_date": "2026-12-01T13:00:00Z",
                "actual_return_date": "2026-12-01T13:00:00Z",
                "book": self.book,
                "user": self.user,
            },
            {
                "borrow_date": timezone.now(),
                "expected_return_date": "2026-12-01T13:00:00Z",
                "book": self.book,
                "user": self.user,
            },
            {
                "borrow_date": timezone.now(),
                "expected_return_date": "2026-12-01T13:00:00Z",
                "book": self.book,
                "user": self.admin,
            },
        ]
        Borrowing.objects.bulk_create([Borrowing(**item) for item in payload])

    def test_filter_borrowings_by_active_and_user_id(self):
        res = self.client.get(
            BORROWING_URL, {"is_active": True, "user_id": self.user.id}
        )
        borrowing = Borrowing.objects.get(user=self.user, actual_return_date=None)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]["id"], borrowing.id)

    def test_admin_can_see_all_borrowings(self):
        res = self.client.get(BORROWING_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 3)
