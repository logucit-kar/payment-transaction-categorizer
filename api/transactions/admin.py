from django.contrib import admin
from .models import Transaction, CategoryData

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('description', 'user_label', 'predicted_category', 'predicted_score', 'created_at')
    search_fields = ('description', 'user_label', 'predicted_category')

@admin.register(CategoryData)
class CategoryDataAdmin(admin.ModelAdmin):
    list_display = ('category_name', 'example_text', 'created_at')
    search_fields = ('category_name', 'example_text')
