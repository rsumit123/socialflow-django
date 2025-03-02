from rest_framework import serializers
from .models import User, ChatSession, ChatMessage, ReportCard, ChatBot

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'password']
        extra_kwargs = {'password': {'write_only': True}}

class ChatSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatSession
        fields = '__all__'

class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = '__all__'

class ReportCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportCard
        fields = '__all__'

class ChatBotListSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatBot
        # Note: 'prompt' is intentionally excluded from the fields list.
        fields = ('id', 'name', 'description', 'created_at', 'updated_at')
