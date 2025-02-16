from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
import os
import requests
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
import json
from drf_yasg import openapi
from dotenv import load_dotenv
import logging
from supabase import create_client, Client
from django.conf import settings

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


logger = logging.getLogger(__name__)

load_dotenv()

class SupabaseGuestLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Anonymous Login via Supabase",
        responses={
            200: "Successful anonymous login",
            500: "Internal server error"
        }
    )
    def post(self, request):
        try:
            data = supabase.auth.sign_in_anonymously()
            data=json.loads(data.model_dump_json())
            # The response structure may vary; adjust as needed.
            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Anonymous login failed: {e}")
            return Response({"error": "Anonymous login failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SupabaseLoginView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Login via Supabase",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="User's email"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, description="User's password"),
            },
            required=["email", "password"]
        ),
        responses={
            200: "Successful authentication",
            400: "Missing email or password",
            401: "Invalid credentials"
        }
    )
    def post(self, request):
        try:
            email = request.data.get("email")
            password = request.data.get("password")
            if not email or not password:
                return Response({"error": "Missing email or password"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                # Use the Supabase SDK to sign in with email and password.
                data = supabase.auth.sign_in_with_password({
                    "email": email,
                    "password": password,
                })
                data=json.loads(data.model_dump_json())
            except Exception as e:
                logger.error(f"Error during login: {e}")
                return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

            #Check for an error in the response from Supabase.
            if data.get("error"):
                logger.error(f"Supabase login error: {data.get('error')}")
                return Response({"error": data.get("error")}, status=status.HTTP_401_UNAUTHORIZED)

            return Response(data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"message": "Error while login", "data": None}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SupabaseRegisterView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_summary="Register a new user via Supabase",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "email": openapi.Schema(type=openapi.TYPE_STRING, description="User's email"),
                "password": openapi.Schema(type=openapi.TYPE_STRING, description="User's password"),
            },
            required=["email", "password"]
        ),
        responses={
            201: "User created successfully",
            400: "Missing email or password",
            409: "User already exists",
            500: "Internal server error"
        }
    )
    def post(self, request):
        try:
            email = request.data.get("email")
            password = request.data.get("password")
            if not email or not password:
                return Response({"error": "Missing email or password"}, status=status.HTTP_400_BAD_REQUEST)


            # Use the Supabase SDK to sign up the user.
            data = supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            data=data.model_dump()
            
            # Check for errors in the response.
            if data.get("error"):
                error_message = data.get("error").get("message", "User already exists")
                logger.error(f"Supabase signup error: {error_message}")
                return Response({"error": error_message}, status=status.HTTP_409_CONFLICT)

            return Response({"message": "User registered successfully", "data": data}, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.exception("Failed to signup")
            if "User already registered" in str(e):
                return Response({"message": "User exists", "data": None}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                return Response({"message": "Problem while signing up", "data": None}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)