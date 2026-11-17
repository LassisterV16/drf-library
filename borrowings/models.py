from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from books.models import Book


class Borrowing(models.Model):
    borrow_date = models.DateTimeField(auto_now_add=True)
    expected_return_date = models.DateTimeField()
    actual_return_date = models.DateTimeField(blank=True, null=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="borrowings")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="borrowings"
    )

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.user.full_name}: {self.book.title} ({self.borrow_date})"

    def return_book(self):
        with transaction.atomic():
            if self.actual_return_date is not None:
                raise ValidationError("This borrowing has already been returned.")

            self.actual_return_date = timezone.now()
            self.save()

            self.book.inventory += 1
            self.book.save()
