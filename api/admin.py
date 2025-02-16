from django.contrib import admin
from .models import ChatMessage, ChatSession, ReportCard, User

admin.site.register(ChatMessage)
admin.site.register(ChatSession)
admin.site.register(ReportCard)
admin.site.register(User)
