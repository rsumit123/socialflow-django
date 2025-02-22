from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

User = get_user_model()

# Content Hierarchy Models

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"


class SubCategory(models.Model):
    category = models.ForeignKey(
        Category,
        related_name='subcategories',
        on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    class Meta:
        verbose_name_plural = "Subcategories"


class Lesson(models.Model):
    subcategory = models.ForeignKey(
        SubCategory,
        related_name='lessons',
        on_delete=models.CASCADE
    )
    title = models.CharField(max_length=100)
    content = models.JSONField()  # Changed from TextField to JSONField to store additional info
    order = models.PositiveIntegerField(default=0)
    max_time = models.PositiveIntegerField(
        default=60,
        help_text="Maximum time in seconds allowed to complete the lesson"
    )
    threshold_score = models.FloatField(
        default=50.0,
        help_text="Minimum score required to complete the lesson"
    )

    def __str__(self):
        return f"{self.subcategory.name} - {self.title}"

    class Meta:
        verbose_name_plural = "Lessons"


# Generic Access Control Model

class UserContentAccess(models.Model):
    """
    Centrally manages access for any content item using generic relations.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    allowed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'content_type', 'object_id')

    def __str__(self):
        status = "Allowed" if self.allowed else "Locked"
        return f"{self.user.email} - {self.content_object} : {status}"


# New Model for Tracking Lesson Progress

class LessonProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lesson_progresses")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress_entries")
    completed = models.BooleanField(default=False)
    score = models.FloatField(default=0)
    time_taken = models.PositiveIntegerField(
        default=0,
        help_text="Time taken by the user in seconds"
    )
    feedback = models.TextField(blank=True)
    attempted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.lesson.title} - Score: {self.score}"

    class Meta:
        verbose_name_plural = "LessonProgresses"


# Optional helper function to check content access

def is_content_accessible(user, content_object):
    ctype = ContentType.objects.get_for_model(content_object)
    try:
        access = UserContentAccess.objects.get(
            user=user,
            content_type=ctype,
            object_id=content_object.pk
        )
        return access.allowed
    except UserContentAccess.DoesNotExist:
        # Default to accessible if no record exists
        return False
