from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse


class LoginRequired(LoginRequiredMixin):
    """
    Mixin that requires user authentication for class-based views.
    Redirects to login page if user is not authenticated.
    """

    redirect_field_name = "next"


def livez(request):
    """
    Simple liveness check endpoint.
    Returns a 200 OK with a JSON message.
    """
    return JsonResponse({"message": "ok"})
