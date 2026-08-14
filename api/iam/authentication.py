import jwt
from jwt import PyJWKClient
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.settings import api_settings


class ServiceUser:
    """Lightweight user wrapper representing the authenticated token payload."""
    def __init__(self, payload):
        self.payload = payload
        self.is_authenticated = True
        self.id = payload.get('userId')
        self.aud = payload.get('aud')
        self.scopes = payload.get('scope', [])

    def has_scope(self, required_scope: str) -> bool:
        return required_scope in self.scopes or f"{self.aud}:*" in self.scopes


class JWKSAuthentication(BaseAuthentication):
    """
    DRF Authentication Class using remote JWKS endpoint from the Auth service.
    """
    def __init__(self):
        self.jwks_client = PyJWKClient(settings.AUTH_JWKS_URL)

    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None

        token = auth_header.split(' ')[1]

        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=api_settings.ALGORITHM,
                audience=settings.CLIENT_ID,
            )
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('Token has expired.')
        except jwt.InvalidAudienceError:
            raise AuthenticationFailed('Token audience does not match this service.')
        except jwt.PyJWTError as e:
            raise AuthenticationFailed(f'Invalid token: {str(e)}')

        return (ServiceUser(payload), token)
