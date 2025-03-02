# views.py
import os
from django.conf import settings
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.authentication import SessionAuthentication, BasicAuthentication

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

class LogFileView(APIView):
    # Override the default authentication to use session and basic auth.
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]

    @swagger_auto_schema(
        operation_summary="View Application Logs",
        operation_description="Returns the content of the current application log file as plain text. Accessible only to admin users.",
        responses={
            200: openapi.Response(
                description="Log file content",
                examples={"text/plain": "DEBUG 2025-03-02 12:00:00 module Some log message..."}
            )
        }
    )
    def get(self, request):
        log_file_path = os.path.join(settings.BASE_DIR, 'logs', 'app.log')
        if not os.path.exists(log_file_path):
            return HttpResponse("Log file not found.", content_type="text/plain", status=404)
        
        with open(log_file_path, 'r') as f:
            log_content = f.read()
        
        return HttpResponse(log_content, content_type="text/plain")