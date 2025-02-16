import requests
import jwt
from django.contrib.auth.backends import BaseBackend
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from datetime import datetime
import pytz
from supabase import create_client, Client
import logging
logger = logging.getLogger(__name__)


User = get_user_model()

supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


class SupabaseAuthentication(BaseAuthentication):
    """
    Custom authentication class to verify Supabase JWT tokens.
    """

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None  # No authentication credentials provided
        try:
            token = auth_header.split(" ")[1]  # Extract the token
        except IndexError:
            token = auth_header
            

        # Validate the token using Supabase API
        # headers = {"Authorization": f"Bearer {token}", "apikey": settings.SUPABASE_ANON_KEY}
        # response = requests.get(f"{settings.SUPABASE_URL}/auth/v1/user", headers=headers)

        response = supabase.auth.get_user(token)

        if not response:
            raise AuthenticationFailed("Invalid Supabase token")

        response = response.model_dump()
        user_data = response.get("user")
        email = user_data.get("email")
        
        

        if user_data.get("is_anonymous") and not email:
            user_id = user_data.get("id")
            email = f"guest_{str(user_id)}@guestuser.com"
            
        if not email:
            raise AuthenticationFailed("Email not found in Supabase token")

        # Ensure user exists in Django and return it
        user, created = User.objects.get_or_create(email=email)
        return user, None  # Now request.user is a Django User instance

class SupabaseAuthBackend(BaseBackend):
    """
    Custom authentication backend for Django that verifies Supabase JWT tokens.
    """

    def authenticate(self, request, token=None):
        if not token:
            return None
        
        headers = {"Authorization": f"Bearer {token}", "apikey": settings.SUPABASE_ANON_KEY}
        response = requests.get(f"{settings.SUPABASE_URL}/auth/v1/user", headers=headers)

        if response.status_code != 200:
            return None  # Token is invalid

        user_data = response.json()
        email = user_data.get("email")

        if not email:
            return None

        # Get or create Django user (this does not create a password)
        user, created = User.objects.get_or_create(email=email)
        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
