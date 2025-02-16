import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import ChatSession, ReportCard

logger = logging.getLogger(__name__)

class ReportCardDetailView(APIView):
    """
    GET /api/chat/sessions/<session_id>/report-card/
    Returns the report card for a specific chat session.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Retrieve report card for a specific session",
        manual_parameters=[
            openapi.Parameter(
                name="session_id",
                in_=openapi.IN_PATH,
                description="Chat session ID",
                type=openapi.TYPE_STRING,
                format="uuid",
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Report card data",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "session_id": openapi.Schema(type=openapi.TYPE_STRING, description="Chat session ID"),
                        "engagement_score": openapi.Schema(type=openapi.TYPE_INTEGER),
                        # "engagement_feedback": openapi.Schema(type=openapi.TYPE_STRING),
                        "humor_score": openapi.Schema(type=openapi.TYPE_INTEGER),
                        # "humor_feedback": openapi.Schema(type=openapi.TYPE_STRING),
                        "empathy_score": openapi.Schema(type=openapi.TYPE_INTEGER),
                        # "empathy_feedback": openapi.Schema(type=openapi.TYPE_STRING),
                        "feedback": openapi.Schema(type=openapi.TYPE_STRING),
                        "total_score": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time")
                    }
                )
            ),
            404: "Not Found"
        }
        ,
        security=[{"Bearer": []}]
    )
    def get(self, request, session_id):
        user = request.user

        try:
            session = ChatSession.objects.get(id=session_id)
        except ChatSession.DoesNotExist:
            return Response({"error": "Chat session not found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            rc = ReportCard.objects.get(session=session)
        except ReportCard.DoesNotExist:
            return Response({"error": "Report card not found for this session."}, status=status.HTTP_404_NOT_FOUND)

        data = {
            "session_id": str(rc.session_id),
            "engagement_score": rc.engagement_score,
            # "engagement_feedback": rc.engagement_feedback,
            "humor_score": rc.humor_score,
            # "humor_feedback": rc.humor_feedback,
            "empathy_score": rc.empathy_score,
            # "empathy_feedback": rc.empathy_feedback,
            "feedback": rc.feedback,
            "total_score": rc.total_score,
            "created_at": rc.created_at.isoformat(),
        }
        return Response(data, status=status.HTTP_200_OK)



class ReportCardListView(APIView):
    """
    GET /api/report-cards/
    Returns all report cards for the current user.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Retrieve all report cards for the current user",
        responses={
            200: openapi.Response(
                description="List of report cards",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "report_cards": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "session_id": openapi.Schema(type=openapi.TYPE_STRING, description="Chat session ID"),
                                    "engagement_score": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    # "engagement_feedback": openapi.Schema(type=openapi.TYPE_STRING),
                                    "humor_score": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    # "humor_feedback": openapi.Schema(type=openapi.TYPE_STRING),
                                    "empathy_score": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    # "empathy_feedback": openapi.Schema(type=openapi.TYPE_STRING),
                                    "feedback": openapi.Schema(type=openapi.TYPE_STRING),
                                    "total_score": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "created_at": openapi.Schema(type=openapi.TYPE_STRING, format="date-time")
                                }
                            )
                        )
                    }
                )
            ),
            404: "Not Found"
        },
        security=[{"Bearer": []}]
    )
    def get(self, request):
        user = request.user
        logger.error(f"GOT USER AS => {user}")
        try:
            report_cards = ReportCard.objects.filter(user=user, total_score__isnull=False)
        except Exception as e:
            logger.error(f"Error retrieving report cards: {e}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        report_cards_data = []
        for rc in report_cards:
            report_cards_data.append({
                "session_id": str(rc.session_id),
                "engagement_score": rc.engagement_score,
                # "engagement_feedback": rc.engagement_feedback,
                "humor_score": rc.humor_score,
                # "humor_feedback": rc.humor_feedback,
                "empathy_score": rc.empathy_score,
                # "empathy_feedback": rc.empathy_feedback,
                "feedback": rc.feedback,
                "total_score": rc.total_score,
                "created_at": rc.created_at.isoformat(),
            })

        return Response({"report_cards": report_cards_data}, status=status.HTTP_200_OK)
