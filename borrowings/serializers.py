from typing import Any

from django.db import transaction
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
        read_only_fields = ("id", "user")

    def validate(self, attrs: Any) -> Any:
        if self.instance is None:
            book = attrs.get("book")
            if book.inventory == 0:
                raise serializers.ValidationError(
                    {"book": "This book is out of stock."}
                )
        return attrs

    def create(self, validated_data: Any):
        with transaction.atomic():
            book = validated_data.get("book")
            borrowing = Borrowing.objects.create(**validated_data)
            book.inventory -= 1
            book.save()
            return borrowing


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
