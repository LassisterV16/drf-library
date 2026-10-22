from rest_framework import serializers

from books.serializers import BookSerializer
from borrowings.models import Borrowing


class BorrowingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return_date",
            "book",
            "user",
        )


class BorrowingUpdateSerializer(BorrowingSerializer):
    class Meta(BorrowingSerializer.Meta):
        fields = BorrowingSerializer.Meta.fields + ("actual_return_date",)


class BorrowingListSerializer(BorrowingUpdateSerializer):
    book = serializers.SlugRelatedField(many=False, read_only=True, slug_field="title")
    user = serializers.SlugRelatedField(
        many=False, read_only=True, slug_field="full_name"
    )


class BorrowingRetrieveSerializer(BorrowingListSerializer):
    book = BookSerializer(many=False, read_only=True)
