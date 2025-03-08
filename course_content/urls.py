from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    SubCategoryViewSet,
    LessonViewSet,
    LessonProgressViewSet,
    EvaluateLessonView,
    TrainingPlanStatusView,  # import the new view
    SubCategoryIntroView  # Add the new view
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'subcategories', SubCategoryViewSet, basename='subcategory')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'lesson-progress', LessonProgressViewSet, basename='lessonprogress')

urlpatterns = [
    path('', include(router.urls)),
    path('training_plan_status/', TrainingPlanStatusView.as_view(), name='training_plan_status'),
    path('evaluate-lesson/', EvaluateLessonView.as_view(), name="evaluate_lesson"),
    path('subcategory-intro/<int:subcategory_id>/', SubCategoryIntroView.as_view(), name="subcategory_intro"),
]
