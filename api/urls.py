from django.urls import path, re_path, include
from .auth_views import (
    SupabaseLoginView, SupabaseRegisterView, SupabaseGuestLoginView
)
from .test_views import ProtectedView, HealthCheck
from .chat_views import ChatSessionView, ChatMessageView, ChatBotListView, ReportGenerationView
from .report_views import ReportCardDetailView, ReportCardListView
from .swagger import schema_view

urlpatterns = [
    # Authentication Endpoints
    path('auth/guest_login/', SupabaseGuestLoginView.as_view(), name="guest_login"),
    path('auth/login/', SupabaseLoginView.as_view(), name="login"),
    path('auth/register/', SupabaseRegisterView.as_view(), name="register"),
    # Protected Routes
    path('protected/', ProtectedView.as_view(), name="protected"),
    path('health/', HealthCheck.as_view(), name="health_check"),
    # Chat Endpoints
    path('chat/sessions/', ChatSessionView.as_view(), name="chat_sessions"),
    path('chat/sessions/<uuid:session_id>/messages/', ChatMessageView.as_view(), name="chat_messages"),
    path('chat/sessions/<uuid:session_id>/generate-report/', ReportGenerationView.as_view(), name="generate_report"),
    path('chat/bots/', ChatBotListView.as_view(), name="chat_bots"),
    # Report Endpoints
    path('report/chat/sessions/<uuid:session_id>/report-card/', ReportCardDetailView.as_view(), name='reportcard-detail'),
    path('report/report-cards/', ReportCardListView.as_view(), name='reportcard-list'),
    # Swagger & ReDoc Documentation
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name="schema-swagger-ui"),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name="schema-redoc"),
    path('swagger.json/', schema_view.without_ui(cache_timeout=0), name="schema-json"),
    # Include new content endpoints
    path('course_content/', include('course_content.urls')),
]
