from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Category, SubCategory, Lesson, LessonProgress, is_content_accessible, UserContentAccess
from .serializers import (
    CategorySerializer,
    SubCategorySerializer,
    LessonSerializer,
    LessonProgressSerializer
)
from django.contrib.contenttypes.models import ContentType

from rest_framework.response import Response
from rest_framework.views import APIView
from api.utils import get_ai_response
from django.shortcuts import get_object_or_404
from rest_framework import status
import logging
import re
import os

logger = logging.getLogger(__name__)
CLIENT_URL = os.getenv('CLIENT_URL', "http://localhost:5173")


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Return all categories (ordering by the 'order' field)
        return Category.objects.all().order_by('order')

    @swagger_auto_schema(
        operation_summary="List all categories",
        operation_description="Retrieve all categories with order and lock status for the authenticated user.",
        responses={200: CategorySerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a specific category",
        operation_description="Retrieve details of a specific category by its ID including lock status.",
        responses={200: CategorySerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)



class SubCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubCategorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = SubCategory.objects.all().order_by('order')
        category_id = self.request.query_params.get('category_id')
        if category_id:
            # Try to fetch the category
            try:
                category = Category.objects.get(pk=category_id)
            except Category.DoesNotExist:
                return qs.none()
            # If the category is locked for the user, return no results.
            if not is_content_accessible(self.request.user, category):
                return qs.none()
            qs = qs.filter(category__id=category_id)
        return qs

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'category_id', 
                openapi.IN_QUERY, 
                description="ID of the category to filter subcategories", 
                type=openapi.TYPE_INTEGER,
                required=False
            )
        ],
        operation_summary="List subcategories for a category",
        operation_description="Retrieve subcategories for a given category with order and lock status.",
        responses={200: SubCategorySerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a specific subcategory",
        operation_description="Retrieve details of a specific subcategory by its ID including lock status.",
        responses={200: SubCategorySerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)


class LessonViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Lesson.objects.all().order_by('order')
        subcategory_id = self.request.query_params.get('subcategory_id')
        if subcategory_id:
            # Try to fetch the subcategory.
            try:
                from .models import SubCategory  # import here if needed
                subcategory = SubCategory.objects.get(pk=subcategory_id)
            except SubCategory.DoesNotExist:
                return qs.none()
            # If the subcategory is locked for the user, return no results.
            if not is_content_accessible(self.request.user, subcategory):
                return qs.none()
            qs = qs.filter(subcategory__id=subcategory_id)
        return qs

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'subcategory_id', 
                openapi.IN_QUERY, 
                description="ID of the subcategory to filter lessons", 
                type=openapi.TYPE_INTEGER,
                required=False
            )
        ],
        operation_summary="List lessons",
        operation_description="Retrieve lessons including JSON content, order, lock status, and any previous progress for the authenticated user.",
        responses={200: LessonSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a specific lesson",
        operation_description="Retrieve details of a specific lesson by its ID including JSON content, order, lock status, and previous progress.",
        responses={200: LessonSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)



class LessonProgressViewSet(viewsets.ModelViewSet):
    """
    ViewSet to track user progress on lessons.
    """
    serializer_class = LessonProgressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = LessonProgress.objects.filter(user=self.request.user)
        lesson_id = self.request.query_params.get('lesson_id')
        if lesson_id:
            qs = qs.filter(lesson__id=lesson_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'lesson_id',
                openapi.IN_QUERY,
                description="Filter progress records by lesson id",
                type=openapi.TYPE_INTEGER,
                required=False
            )
        ],
        operation_summary="List lesson progress",
        operation_description="Retrieve a list of lesson progress records for the authenticated user. Optionally, filter by lesson_id.",
        responses={200: LessonProgressSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Retrieve a lesson progress record",
        operation_description="Retrieve details of a specific lesson progress record by its ID.",
        responses={200: LessonProgressSerializer()}
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @swagger_auto_schema(
        operation_summary="Create a lesson progress record",
        operation_description="Submit a new lesson progress record including score, time taken, and feedback.",
        request_body=LessonProgressSerializer,
        responses={201: LessonProgressSerializer()}
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


class TrainingPlanStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Training Plan Status",
        operation_description=(
            "Returns the training plan status based on whether any one of the categories "
            "is unlocked for the authenticated user. If at least one category is unlocked, "
            "is_locked will be False; otherwise, it will be True."
        ),
        responses={200: openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'is_locked': openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Training plan lock status")
            }
        )}
    )
    def get(self, request, format=None):
        new_user = False

        # Unlock Category with id=4 if not already unlocked.
        try:
            category = Category.objects.get(pk=4)
            category_ctype = ContentType.objects.get_for_model(Category)
            access, created = UserContentAccess.objects.get_or_create(
                user=request.user,
                content_type=category_ctype,
                object_id=category.pk,
                defaults={'allowed': True}
            )
            if created:
                new_user = True
                logger.info("Category unlocked for the first time.")
            elif not access.allowed:
                access.allowed = True
                access.save()
                new_user = True
                logger.info("Category was locked and is now unlocked.")
        except Category.DoesNotExist:
            logger.error("Category with id 4 not found.")

        # Unlock Subcategory with id=12 if not already unlocked.
        try:
            subcategory = SubCategory.objects.get(pk=12)
            subcategory_ctype = ContentType.objects.get_for_model(SubCategory)
            access, created = UserContentAccess.objects.get_or_create(
                user=request.user,
                content_type=subcategory_ctype,
                object_id=subcategory.pk,
                defaults={'allowed': True}
            )
            if created:
                new_user = True
                logger.info("Subcategory unlocked for the first time.")
            elif not access.allowed:
                access.allowed = True
                access.save()
                new_user = True
                logger.info("Subcategory was locked and is now unlocked.")
        except SubCategory.DoesNotExist:
            logger.error("Subcategory with id 12 not found.")

        # Unlock Lesson with id=19 if not already unlocked.
        try:
            lesson = Lesson.objects.get(pk=19)
            lesson_ctype = ContentType.objects.get_for_model(Lesson)
            access, created = UserContentAccess.objects.get_or_create(
                user=request.user,
                content_type=lesson_ctype,
                object_id=lesson.pk,
                defaults={'allowed': True}
            )
            if created:
                new_user = True
                logger.info("Lesson unlocked for the first time.")
            elif not access.allowed:
                access.allowed = True
                access.save()
                new_user = True
                logger.info("Lesson was locked and is now unlocked.")
        except Lesson.DoesNotExist:
            logger.error("Lesson with id 19 not found.")

        # Retrieve all categories and determine if at least one category is unlocked.
        categories = Category.objects.all()
        any_unlocked = any(is_content_accessible(request.user, category) for category in categories)
        is_locked = not any_unlocked

        return Response(
            {"is_locked": is_locked, "new_user": new_user},
            status=status.HTTP_200_OK
        )




class EvaluateLessonView(APIView):
    """
    API to evaluate a user's lesson attempt.
    The client must send lesson_id, user_response, and time_taken.
    The AI evaluator returns a score (0-100) and brief feedback.
    If the score is >= lesson.threshold_score and time_taken < lesson.max_time,
    the lesson is marked as completed and the next lesson (if any) is unlocked.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Evaluate a lesson attempt",
        operation_description=(
            "Evaluates the user's lesson attempt by sending a prompt with the lesson context, objective, "
            "user response, and evaluation criteria to the AI. Returns a score, feedback, and a completion status. "
            "If the lesson is completed, the next lesson in sequence will be unlocked for the user."
        ),
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["lesson_id", "user_response", "time_taken"],
            properties={
                "lesson_id": openapi.Schema(type=openapi.TYPE_INTEGER, description="ID of the lesson"),
                "user_response": openapi.Schema(type=openapi.TYPE_STRING, description="User's response (can be empty)"),
                "time_taken": openapi.Schema(type=openapi.TYPE_INTEGER, description="Time taken in seconds")
            }
        ),
        responses={
            200: openapi.Response(
                description="Evaluation result",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "score": openapi.Schema(type=openapi.TYPE_NUMBER, description="Score out of 100"),
                        "feedback": openapi.Schema(type=openapi.TYPE_STRING, description="Brief feedback (max 20 words)"),
                        "completed": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Lesson completion status")
                    }
                )
            ),
            400: "Bad Request",
            500: "Internal Server Error"
        }
    )
    def post(self, request):
        try:
            lesson_id = request.data.get("lesson_id")
            user_response = request.data.get("user_response", "")
            time_taken = request.data.get("time_taken")

            if not lesson_id or time_taken is None:
                return Response(
                    {"error": "Missing required fields: lesson_id and time_taken"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Retrieve the lesson instance
            lesson = get_object_or_404(Lesson, id=lesson_id)

            # Extract details from the lesson's JSON content.
            # It's assumed that the content field includes keys like 'Context', 'Objective', and optionally 'Feedback Focus'.
            content = lesson.content or {}
            context_text = content.get("Context", "No context provided")
            objective_text = content.get("Objective", "No objective provided")
            evaluation_criteria = content.get("Feedback Focus", "Provide a creative and authentic response")

            if user_response.strip() == "" or len(user_response) < 5:
                # If the user response is empty, return a default response.
                feedback = "Oops! Looks like you created an awkward moment. No response provided."
                LessonProgress.objects.create(
                user=request.user,
                lesson=lesson,
                completed=False,
                score=0,
                time_taken=time_taken,
                feedback=feedback
                )
                return Response({
                "score": 0,
                "feedback": feedback,
                "completed": False
                }, status=status.HTTP_200_OK)

            # Build prompt messages for the AI evaluator.
            prompt_messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a social skills trainer and evaluator. Given a specific scenario and context, "
                        "evaluate the following response by the user. Provide a score out of 100 and brief feedback "
                        "that is helpful to the users. Your tone should be positive in general. Like you did this good,"
                        "but you can improve this. The feedback should be concise and to the point. "
                        "Remember users' response should always take into account the context, if not provide that in your feedback and decrease score."
                        "The feedback should be constructive and actionable. "
                        "The feedback should be specific and clear. "
                        "The feedback should be encouraging and motivating. "
                        "Never give examples as to how users' should response in your feedback. "
                        f"Remember the score is out of 100 and the passing score is {lesson.threshold_score}, give a score"
                        "above this only when you feel the user was almost perfect. Also your feedback should be"
                        "no more than 20 words. Format your answer as: 'score: <score>, feedback: <feedback>'."
                    )
                },
                {
                    "role": "user",
                    "content": (
                        f"Context: {context_text}\n"
                        f"Objective: {objective_text}\n"
                        f"Evaluation Criteria: {evaluation_criteria}\n"
                        f"User Response: {user_response}"
                    )
                }
            ]

            # Call the AI evaluator
            ai_response = get_ai_response(prompt_messages, temperature=1.3)
            logger.info(f"AI evaluation response: {ai_response}")

            # Parse the AI response using a regex pattern.
            # Expected format: "score: <score>, feedback: <feedback>"
            pattern = r"score:\s*(?P<score>\d+(?:\.\d+)?),\s*feedback:\s*(?P<feedback>.+)"
            match = re.search(pattern, ai_response, re.IGNORECASE)
            if match:
                score_str = match.group("score")
                feedback = match.group("feedback").strip()
                score = float(score_str)
            else:
                raise ValueError("Could not parse score or feedback from AI response.")

            # Determine completion status.
            # Lesson is completed if score >= lesson.threshold_score and time_taken < lesson.max_time.
            completed = (score >= lesson.threshold_score) and (time_taken < lesson.max_time)

            # Record the lesson progress.
            LessonProgress.objects.create(
                user=request.user,
                lesson=lesson,
                completed=completed,
                score=score,
                time_taken=time_taken,
                feedback=feedback
            )

            # If the lesson is completed, unlock the next lesson (if any).
            if completed:
                next_lesson = (
                    Lesson.objects
                    .filter(subcategory=lesson.subcategory, order=lesson.order + 1)
                    .first()
                )
                next_lesson_id = 0
                if next_lesson:
                    next_lesson_id = next_lesson.id
                    ctype = ContentType.objects.get_for_model(next_lesson)
                    access, created = UserContentAccess.objects.get_or_create(
                        user=request.user,
                        content_type=ctype,
                        object_id=next_lesson.pk,
                        defaults={'allowed': True}
                    )
                    if not created and not access.allowed:
                        access.allowed = True
                        access.save()
                    logger.info(f"Next lesson unlocked: {next_lesson}")

            return Response({
                "score": score,
                "feedback": feedback,
                "completed": completed,
                "next_lesson_url": f"{CLIENT_URL}/training/lessondetail/{next_lesson_id}" if completed else None
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("Exception during lesson evaluation.")
            return Response(
                {"error": "An error occurred during evaluation", "detail": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class SubCategoryIntroView(APIView):
    """
    API to return the subcategory intro content.
    This will be displayed as a reading lesson for users in the UI.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Get subcategory intro",
        operation_description=(
            "Returns the subcategory intro content including title, intro text, and objective. "
            "This will be displayed as a reading lesson for users in the UI."
        ),
        manual_parameters=[
            openapi.Parameter(
                'subcategory_id',
                openapi.IN_PATH,
                description="ID of the subcategory",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Subcategory intro content",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "id": openapi.Schema(type=openapi.TYPE_INTEGER, description="Subcategory ID"),
                        "title": openapi.Schema(type=openapi.TYPE_STRING, description="Subcategory name"),
                        "intro": openapi.Schema(type=openapi.TYPE_STRING, description="Subcategory introduction content"),
                        "objective": openapi.Schema(type=openapi.TYPE_STRING, description="Learning objective for this subcategory"),
                        "is_locked": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Whether this subcategory is locked for the user")
                    }
                )
            ),
            404: "Subcategory not found"
        }
    )
    def get(self, request, subcategory_id):
        try:
            subcategory = SubCategory.objects.get(id=subcategory_id)
            
            # Check if the subcategory is accessible to the user
            is_locked = not is_content_accessible(request.user, subcategory)
            
            # Create a response with the subcategory intro content
            response_data = {
                "id": subcategory.id,
                "title": subcategory.name,
                "intro": subcategory.intro or f"Welcome to {subcategory.name}. This section will introduce you to the key concepts and ideas.",
                "objective": subcategory.objective or f"Learn about {subcategory.name} and understand its key concepts.",
                "is_locked": is_locked
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except SubCategory.DoesNotExist:
            return Response(
                {"error": "Subcategory not found"},
                status=status.HTTP_404_NOT_FOUND
            )



    