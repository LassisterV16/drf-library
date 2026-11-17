from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from borrowings.models import Borrowing
from borrowings.permissions import IsAdminOrOwner
from borrowings.serializers import (
    BorrowingSerializer,
    BorrowingUpdateSerializer,
    BorrowingListSerializer,
    BorrowingRetrieveSerializer,
)


class BorrowingViewSet(viewsets.ModelViewSet):
    queryset = Borrowing.objects.all()
    serializer_class = BorrowingSerializer
    permission_classes = (IsAdminOrOwner,)

    def get_queryset(self):
        queryset = Borrowing.objects.select_related("book", "user")

        is_active = self.request.query_params.get("is_active")
        user_id = self.request.query_params.get("user_id")

        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)

        if is_active:
            queryset = queryset.filter(actual_return_date=None)

        if user_id and self.request.user.is_staff:
            queryset = queryset.filter(user=user_id)

        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return BorrowingListSerializer

        if self.action == "retrieve":
            return BorrowingRetrieveSerializer

        if self.action in ("update", "partial_update"):
            return BorrowingUpdateSerializer

        return BorrowingSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        summary="Return a borrowed book",
        description="Marks the borrowing as returned, "
        "updates actual return date, "
        "and increases the book inventory by 1.",
        request=None,
        responses={
            200: OpenApiResponse(
                description="Book returned successfully.",
                response={
                    "type": "object",
                    "properties": {
                        "detail": {"type": "string", "example": "Book returned successfully."}
                    }
                }
            ),
            400: OpenApiResponse(
                description="Bad Request (e.g., already returned).",
                response={
                    "type": "object",
                    "properties": {
                        "non_field_errors": {
                            "type": "array",
                            "items": {"type": "string"},
                            "example": ["This borrowing has already been returned."]
                        }
                    }
                }
            ),
        },
    )
    @action(detail=True, methods=["post"])
    def return_borrowing(self, request, pk=None):
        borrowing = self.get_object()
        borrowing.return_book()
        return Response(
            {"detail": "Book returned successfully."}, status=status.HTTP_200_OK
        )
