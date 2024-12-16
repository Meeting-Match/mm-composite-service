# from rest_framework.authentication import BaseAuthentication
import requests
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed
import logging

logger = logging.getLogger("composite")

def get_correlation_id(request):
    return getattr(request, "correlation_id", "N/A")

class RemoteJWTAuthentication(JWTAuthentication):
    AUTH_SERVICE_URL = "http://3.15.225.226:8001/userinfo/" ############################################################

    def get_header(self, request):
        correlation_id = get_correlation_id(request)
        header = request.headers.get("Authorization")
        if isinstance(header, bytes):
            header = header.decode("utf-8")
        logger.debug(f'Authorization header retrieved', extra={'correlation_id': correlation_id})
        return header

    def authenticate(self, request):
        correlation_id = get_correlation_id(request)
        logger.info('Authenticating user via remote JWT', extra={'correlation_id': correlation_id})

        try:
            validated_token = self.get_validated_token(self.get_raw_token(request))
            user_info = self.fetch_user_info(validated_token, correlation_id)

            if not user_info:
                logger.error('User not found during authentication', extra={'correlation_id': correlation_id})
                raise AuthenticationFailed("User not found")

            request.user = self.create_user_representation(user_info)
            logger.info(f'User authenticated successfully: {request.user}', extra={'correlation_id': correlation_id})
            return (request.user, validated_token)

        except AuthenticationFailed as e:
            logger.warning(f'Authentication failed: {str(e)}', extra={'correlation_id': correlation_id})
            raise
        except Exception as e:
            logger.error(f'Unexpected error during authentication: {str(e)}', extra={'correlation_id': correlation_id})
            raise

    def fetch_user_info(self, token, correlation_id):
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Correlation-ID": correlation_id
        }
        logger.debug(f'Fetching user info from {self.AUTH_SERVICE_URL}', extra={'correlation_id': correlation_id})
        try:
            response = requests.get(self.AUTH_SERVICE_URL, headers=headers)
            logger.info(f'Auth service response status: {response.status_code}', extra={'correlation_id': correlation_id})
            if response.status_code == 200:
                logger.debug('User info retrieved successfully', extra={'correlation_id': correlation_id})
                return response.json()
            else:
                logger.warning(f'Auth service returned status {response.status_code}', extra={'correlation_id': correlation_id})
        except requests.RequestException as e:
            logger.error(f'Error fetching user info: {e}', extra={'correlation_id': correlation_id})
        return None

    def create_user_representation(self, user_info):
        logger.debug(f'Creating user representation for {user_info}')
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
        correlation_id = get_correlation_id(request)
        header = self.get_header(request)
        if not header:
            logger.warning('Authorization header missing', extra={'correlation_id': correlation_id})
            raise AuthenticationFailed("Authorization header missing")

        # Debug the header
        logger.debug('Authorization header found', extra={'correlation_id': correlation_id})

        # Extract token
        parts = header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            logger.error("Authorization header must be 'Bearer <token>'", extra={'correlation_id': correlation_id})
            raise AuthenticationFailed(
                "Authorization header must be 'Bearer <token>'")

        return parts[1]
