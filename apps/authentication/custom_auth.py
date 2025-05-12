from django.contrib.auth import get_user_model
from rest_framework import authentication
from rest_framework import exceptions
import logging

logger = logging.getLogger('django')

User = get_user_model()

class DebugAuthentication(authentication.BaseAuthentication):
    """
    A debug authentication class that logs user authentication details
    and fixes string username issues.
    """
    
    def authenticate(self, request):
        # Check if there's already an authenticated user
        user = getattr(request, 'user', None)
        
        # Log what we received
        logger.debug(f"DebugAuthentication received user: {user} (type: {type(user)})")
        
        # If user is a string (username), convert to User instance
        if isinstance(user, str):
            logger.debug(f"Converting string username '{user}' to User instance")
            try:
                user = User.objects.get(username=user)
                logger.debug(f"Converted successfully to User: {user}")
                return (user, None)  # Return the User instance
            except User.DoesNotExist:
                logger.error(f"Username '{user}' not found in database")
                raise exceptions.AuthenticationFailed('User not found')
        
        # If we already have a User instance, return it
        if user and user.is_authenticated:
            logger.debug(f"User is already authenticated: {user}")
            return (user, None)
        
        # No credentials provided
        return None