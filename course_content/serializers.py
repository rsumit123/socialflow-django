from rest_framework import serializers
from .models import Category, SubCategory, Lesson, LessonProgress, is_content_accessible

class CategorySerializer(serializers.ModelSerializer):
    is_locked = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'description', 'order', 'is_locked']

    def get_is_locked(self, obj):
        request = self.context.get('request')
        if request:
            # If the user does not have access, then it is locked.
            return not is_content_accessible(request.user, obj)
        return False

class SubCategorySerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    is_locked = serializers.SerializerMethodField()

    class Meta:
        model = SubCategory
        fields = ['id', 'name', 'description', 'objective', 'intro', 'order', 'category', 'is_locked']

    def get_is_locked(self, obj):
        request = self.context.get('request')
        if request:
            return not is_content_accessible(request.user, obj)
        return False

# A nested serializer to show a user's progress on a lesson
class UserLessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = ['score', 'time_taken', 'completed', 'feedback', 'attempted_at']

class LessonSerializer(serializers.ModelSerializer):
    subcategory = SubCategorySerializer(read_only=True)
    is_locked = serializers.SerializerMethodField()
    previous_progress = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = [
            'id',
            'title',
            'content',  # Now a JSON field
            'order',
            'subcategory',
            'max_time',
            'threshold_score',
            'is_locked',
            'previous_progress'
        ]

    def get_is_locked(self, obj):
        request = self.context.get('request')
        if request:
            return not is_content_accessible(request.user, obj)
        return False

    def get_previous_progress(self, obj):
        request = self.context.get('request')
        if request:
            # Get all progress entries for this lesson and the current user
            progresses = obj.progress_entries.filter(user=request.user)
            return UserLessonProgressSerializer(progresses, many=True).data
        return []

class LessonProgressSerializer(serializers.ModelSerializer):
    lesson = LessonSerializer(read_only=True)
    lesson_id = serializers.PrimaryKeyRelatedField(
        queryset=Lesson.objects.all(), write_only=True, source='lesson'
    )
    
    class Meta:
        model = LessonProgress
        fields = [
            'id',
            'user',
            'lesson',
            'lesson_id',
            'completed',
            'score',
            'time_taken',
            'feedback',
            'attempted_at'
        ]
        read_only_fields = ['user', 'attempted_at', 'lesson']



