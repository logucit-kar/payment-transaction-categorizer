from django.contrib import admin
from django.urls import include, path
from rest_framework import routers

from apps.transactions.views import (
    CategoryDataViewSet,
    TransactionViewSet,
    UploadBatchViewSet,
    export_transactions_csv,
    export_transactions_json,
    low_confidence_submit,
    upload_file,
    upload_stream,
)

router = routers.DefaultRouter()
router.register(r"transactions", TransactionViewSet, basename="transaction")
router.register(r"category-data", CategoryDataViewSet, basename="categorydata")
router.register(r"batches", UploadBatchViewSet, basename="batches")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/upload/", upload_file),
    path("api/upload/stream/<int:batch_id>/", upload_stream),
    path("api/low-confidence/submit/", low_confidence_submit),
    path("api/transactions/export/csv/", export_transactions_csv),
    path("api/transactions/export/json/", export_transactions_json),
]
