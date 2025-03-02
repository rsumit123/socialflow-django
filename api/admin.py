from django.contrib import admin
from .models import ChatMessage, ChatSession, ReportCard, User, ChatBot

admin.site.register(ChatMessage)
admin.site.register(ChatSession)
admin.site.register(ReportCard)
admin.site.register(ChatBot)

admin.site.register(User)
