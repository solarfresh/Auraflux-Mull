from rest_framework.permissions import BasePermission


class HasRequiredScope(BasePermission):
    """
    Permission class checking if the authenticated user/service has the required scope.
    Usage in View: required_scope = 'biz-system-b:read'

    Example:
        class MyView(APIView):
            required_scope = 'biz-system-b:read'
            permission_classes = [HasRequiredScope]
    """
    def has_permission(self, request, view):
        if not request.user or not getattr(request.user, 'is_authenticated', False):
            return False

        required_scope = getattr(view, 'required_scope', None)
        if not required_scope:
            return True

        return request.user.has_scope(required_scope)
