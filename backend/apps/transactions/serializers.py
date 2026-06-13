from rest_framework import serializers
from .models import Transaction, CategoryData
from .models import UploadBatch, UploadItem

class CategoryDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryData
        fields = '__all__'


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = '__all__'

class UploadItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadItem
        fields = ['id', 'payload', 'processed', 'saved', 'error', 'created_at']

class UploadBatchSerializer(serializers.ModelSerializer):
    items = UploadItemSerializer(many=True, read_only=True)
    class Meta:
        model = UploadBatch
        fields = ['id', 'filename', 'total_items', 'processed', 'saved', 'status', 'created_at', 'updated_at', 'items']