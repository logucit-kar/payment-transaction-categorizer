from django.db import models

class CategoryData(models.Model):
    category_name = models.CharField(max_length=200)
    example_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.category_name}: {self.example_text[:30]}"


class Transaction(models.Model):
    description = models.TextField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    user_label = models.CharField(max_length=200, null=True, blank=True)
    predicted_category = models.CharField(max_length=200, null=True, blank=True)
    predicted_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # store NER entities as JSON string if needed (optional)
    entities = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.description[:50]} ({self.predicted_category})"


class UploadBatch(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In progress'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]
    #created_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL)
    filename = models.CharField(max_length=255, null=True, blank=True)
    total_items = models.IntegerField(default=0)
    processed = models.IntegerField(default=0)
    saved = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    metadata = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    low_confidence = models.JSONField(default=list, blank=True)

class UploadItem(models.Model):
    batch = models.ForeignKey(UploadBatch, related_name='items', on_delete=models.CASCADE)
    payload = models.JSONField()
    processed = models.BooleanField(default=False)
    saved = models.BooleanField(default=False)
    error = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
