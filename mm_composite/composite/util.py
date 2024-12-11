# from rest_framework.authentication import BaseAuthentication
import requests
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed


class RemoteJWTAuthentication(JWTAuthentication):
    AUTH_SERVICE_URL = "http://localhost:8001/userinfo/"

    def get_header(self, request):
        header = request.headers.get("Authorization")
        if isinstance(header, bytes):
            header = header.decode("utf-8")
        return header

    def authenticate(self, request):
        validated_token = self.get_validated_token(self.get_raw_token(request))
        user_info = self.fetch_user_info(validated_token)

        if not user_info:
            raise AuthenticationFailed("User not found")

        request.user = self.create_user_representation(user_info)
        return (request.user, validated_token)

    def fetch_user_info(self, token):
        headers = {"Authorization": f"Bearer {token}"}
        try:
            response = requests.get(self.AUTH_SERVICE_URL, headers=headers)
            if response.status_code == 200:
                return response.json()
        except requests.RequestException:
            pass
        return None

    def create_user_representation(self, user_info):
        # Create a simple user-like object
        class RemoteUser:
            def __init__(self, info):
                self.id = info.get("id")
                self.username = info.get("username")
                self.email = info.get("email")
                self.is_authenticated = True  # Django requires this

            def __str__(self):
                return self.username or "Anonymous"

        return RemoteUser(user_info)

    def get_raw_token(self, request):
        header = self.get_header(request)
        if not header:
            raise AuthenticationFailed("Authorization header missing")

        # Debug the header
        print("Authorization Header:", header)

        # Extract token
        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise AuthenticationFailed(
                "Authorization header must be 'Bearer <token>'")

        return parts[1]
