from .utils import get_ai_response, process_evaluation
from .models import User, ChatSession, ChatMessage, ReportCard, ChatBot
from .serializers import UserSerializer, ChatSessionSerializer, ChatMessageSerializer, ReportCardSerializer, ChatBotListSerializer
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from drf_yasg.utils import swagger_auto_schema
import random
from drf_yasg import openapi
from django.conf import settings
import json
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
import os
from dotenv import load_dotenv
from django.utils.html import escape
from django.db import transaction
from rest_framework import status



load_dotenv()
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

# Load scenarios from a JSON file or a predefined list
try:
    with open(settings.SCENARIOS_FILE_PATH, 'r') as file:
        SCENARIOS = json.load(file)
        logger.info(f"Loaded {len(SCENARIOS)} scenarios from scenarios.json.")
except FileNotFoundError:
    logger.error(f"scenarios.json file not found at {settings.SCENARIOS_FILE_PATH}.")
    SCENARIOS = []
except json.JSONDecodeError as e:
    logger.error(f"Error decoding JSON from scenarios.json: {e}")
    SCENARIOS = []

INITIAL_PROMPT = os.getenv('INITIAL_PROMPT_V2', "Welcome! Let's start chatting.")
EVALUATION_PROMPT = os.getenv('EVALUATION_PROMPT', "Welcome! Let's start chatting.")
CLIENT_URL = os.getenv("CLIENT_URL", "https://socialflow.skdev.one")
MAX_MESSAGES = 20



class ChatBotListView(APIView):
    # Adjust permission_classes as needed (e.g., IsAuthenticated)
    permission_classes = []

    @swagger_auto_schema(
        operation_summary="List Chat Bots",
        operation_description="Returns a list of available chat bots (without the prompt field).",
        responses={200: ChatBotListSerializer(many=True)}
    )
    def get(self, request, format=None):
        bots = ChatBot.objects.all()
        serializer = ChatBotListSerializer(bots, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
class ChatSessionView(APIView):
    """
    API to create a new chat session.
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Create a new chat session",
        operation_description="Starts a new chat session and returns an initial AI-generated message. Accepts an optional bot_id parameter.",
        manual_parameters=[
            openapi.Parameter(
                "Authorization",
                openapi.IN_HEADER,
                description="Bearer JWT token",
                type=openapi.TYPE_STRING,
                required=True,
            ),
            openapi.Parameter(
                "bot_id",
                openapi.IN_QUERY,
                description="ID of the selected ChatBot (optional). Defaults to the first available bot if not provided.",
                type=openapi.TYPE_INTEGER,
                required=False
            )
        ],
        responses={
            201: openapi.Response(
                "Chat session created successfully",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "message": openapi.Schema(type=openapi.TYPE_STRING, description="Success message"),
                        "session_id": openapi.Schema(type=openapi.TYPE_STRING, format="uuid", description="ID of the created chat session"),
                        "ai_response": openapi.Schema(type=openapi.TYPE_STRING, description="Initial AI response"),
                        "custom_scenario": openapi.Schema(type=openapi.TYPE_STRING, description="Scenario used for AI chat"),
                    }
                )
            ),
            500: "Internal Server Error"
        }
    )
    def post(self, request):
        try:
            # Ensure the user is properly authenticated
            if not isinstance(request.user, User):
                return Response({"error": "User is not authenticated correctly"}, status=400)

            # 1. Retrieve bot_id from the request data or query parameters
            bot_id = request.data.get("bot_id") or request.query_params.get("bot_id")
            if bot_id:
                try:
                    bot = ChatBot.objects.get(pk=bot_id)
                except ChatBot.DoesNotExist:
                    logger.error("Invalid bot_id provided, defaulting to first available ChatBot.")
                    bot = ChatBot.objects.first()
            else:
                bot = ChatBot.objects.first()

            if not bot:
                logger.error("No ChatBot available in the system.")
                return Response({"error": "No ChatBot available."}, status=500)

            # 2. Create a new ChatSession and attach the selected ChatBot
            chat_session = ChatSession.objects.create(user=request.user, bot=bot)

            # 3. Select a random scenario
            if not SCENARIOS:
                logger.error("No scenarios available to select.")
                return Response({"error": "No scenarios available. Please contact support."}, status=500)

            selected_scenario = random.choice(SCENARIOS)

            # 4. Format the prompt using the selected bot's prompt instead of INITIAL_PROMPT
            formatted_initial_prompt = bot.prompt.format(
                name=selected_scenario["ai_name"],
                custom_role=selected_scenario["ai_role"]
            )

            # 5. Save the formatted system message with the custom scenario
            system_message = ChatMessage.objects.create(
                session=chat_session,
                sender="system",
                content=formatted_initial_prompt
            )

            # 6. Prepare messages for the AI (including the formatted system message)
            messages = [{"role": "system", "content": formatted_initial_prompt}]

            # 7. Get AI response to the initial prompt
            ai_response = get_ai_response(messages)

            # 8. Save the AI response
            ai_msg = ChatMessage.objects.create(
                session=chat_session,
                sender="assistant",
                content=ai_response
            )

            return Response({
                "message": "Chat session created successfully",
                "session_id": chat_session.id,
                "ai_response": ai_msg.content,
                "custom_scenario": selected_scenario
            }, status=201)

        except Exception as e:
            logger.exception(f"Error creating chat session: {e}")
            return Response({
                "message": f"Chat session not created due to error | {e}",
                "session_id": None,
                "ai_response": None
            }, status=500)


class ChatMessageView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Send a message in a chat session",
        operation_description="Sends a user message to the chat session and gets an AI response.",
        manual_parameters=[
            openapi.Parameter(
                name="session_id",
                in_=openapi.IN_PATH,
                description="Chat session ID",
                type=openapi.TYPE_STRING,
                format="uuid",
                required=True,
            ),
            openapi.Parameter(
                name="Authorization",
                in_=openapi.IN_HEADER,
                description="Bearer JWT token",
                type=openapi.TYPE_STRING,
                required=True,
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["message"],
            properties={
                "message": openapi.Schema(
                    type=openapi.TYPE_STRING, 
                    description="User message to send"
                )
            },
        ),
        responses={
            200: openapi.Response(
                "Message sent successfully",
                openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "user_message": openapi.Schema(
                            type=openapi.TYPE_STRING, 
                            description="Message sent by the user"
                        ),
                        "ai_response": openapi.Schema(
                            type=openapi.TYPE_STRING, 
                            description="Response from the AI"
                        ),
                    }
                )
            ),
            404: "Chat session not found",
            401: "Unauthorized - Bearer token required",
        },
        security=[{"Bearer": []}]
    )
    @transaction.atomic
    def post(self, request, session_id):
        try:
            data = request.data
            user_message = data.get("message")
            if not user_message:
                return Response(
                    {"error": "Missing 'message' in request"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Sanitize the user message
            user_message = escape(user_message)

            # logger.error(f"Found user => {request.user}")


            # Retrieve the chat session for the current user
            session = ChatSession.objects.filter(id=session_id).first()
            if not session:
                return Response(
                    {"error": "Chat session not found"},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Save the user message
            user_msg = ChatMessage.objects.create(
                session=session, sender="user", content=user_message
            )

            # Gather all user messages (as strings)
            user_messages = list(
                session.messages.filter(sender="user").values_list("content", flat=True)
            )
            # Retrieve and join any system messages for context
            system_qs = session.messages.filter(sender="system")
            system_msg = (
                " ".join(system_qs.values_list("content", flat=True))
                if system_qs.exists() else ""
            )

            # Retrieve messages (user and assistant) ordered by creation time
            ai_msgs_qs = session.messages.filter(sender__in=["user", "assistant"]).order_by("timestamp")
            messages = [
                {"role": msg.sender, "content": msg.content}
                for msg in ai_msgs_qs
            ]
            # Prepend system message if it exists
            if system_msg:
                messages.insert(0, {"role": "system", "content": system_msg})
            # Limit context to the last MAX_MESSAGES if needed
            if len(messages) > MAX_MESSAGES:
                messages = messages[-MAX_MESSAGES:]

            # Get AI response based on the conversation context
            ai_response = get_ai_response(messages)
            ai_msg = ChatMessage.objects.create(
                session=session, sender="assistant", content=ai_response
            )

            lower_message = user_message.lower()
            # Include the current message in the count
            user_message_count = len(user_messages) + 1

            # If fewer than 10 messages and the user hasn't signaled an end...
            if user_message_count < 10 and not (
                "end chat" in lower_message or "end this chat" in lower_message
            ):
                return Response({
                    "user_message": user_msg.content,
                    "ai_response": ai_msg.content
                }, status=status.HTTP_200_OK)

            # If exactly 10 messages or the user signals end-of-chat, trigger evaluation
            elif user_message_count == 10 or (
                "end chat" in lower_message or "end this chat" in lower_message
            ):
                # Refresh messages for evaluation
                updated_user_messages = list(
                    session.messages.filter(sender="user").values_list("content", flat=True)
                )
                ai_messages = list(
                    session.messages.filter(sender="assistant").values_list("content", flat=True)
                )
                report_card, feedback, unlocked_cat, unlocked_sub, unlocked_lesson = process_evaluation(
                    session, updated_user_messages, ai_messages, session_id, request.user
                )
                if user_message_count == 10:
                    response_data = {
                        "user_message": user_msg.content,
                        "ai_response": ai_msg.content,
                        "evaluation": {
                            "engagement_score": report_card.engagement_score,
                            # "engagement_feedback": report_card.engagement_feedback,
                            "humor_score": report_card.humor_score,
                            # "humor_feedback": report_card.humor_feedback,
                            "empathy_score": report_card.empathy_score,
                            # "empathy_feedback": report_card.empathy_feedback,
                            "total_score": report_card.total_score,
                            "feedback_summary": feedback,
                            "feedback": feedback,
                            "unlocked_content": True if unlocked_cat or unlocked_sub or unlocked_lesson else False,
                            "report_link": f"{CLIENT_URL}/report-cards/{session_id}"
                        }
                    }
                else:
                    response_data = {
                        "user_message": user_msg.content,
                        "ai_response": "You have completed the game! Your performance has been evaluated. Go to Report Cards to view your Score.",
                        "evaluation": {
                            "engagement_score": report_card.engagement_score,
                            "humor_score": report_card.humor_score,
                            "empathy_score": report_card.empathy_score,
                            "total_score": report_card.total_score,
                            "feedback_summary": feedback,
                            "unlocked_content": True if unlocked_cat or unlocked_sub or unlocked_lesson else False,
                            "feedback": feedback,
                            "report_link": f"{CLIENT_URL}/report-cards/{session_id}"
                        }
                    }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response({
                    "user_message": user_msg.content,
                    "ai_response": ai_msg.content
                }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Error handling chat message: {e}")
            transaction.set_rollback(True)
            return Response(
                {"error": "Internal server error"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
