from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from dotenv import load_dotenv
import logging


# Protected Route
class ProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": f"Hello, {request.user.email}!"})
    

# HealthCheck
class HealthCheck(APIView):
    @swagger_auto_schema(
        operation_summary="Check server health",
        responses={200: "Server is running"}
    )

    def get(self, request):
        return Response({"message": f"Hello, I am running!"})