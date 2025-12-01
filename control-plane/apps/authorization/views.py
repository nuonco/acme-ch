from django_registration.backends.one_step.views import RegistrationView
from django.contrib.auth.views import LoginView, LogoutView
from django.conf import settings

from common.views import LoginRequired


class Login(LoginView):
    template_name = "login.html"
    redirect_authenticated_user = True
    extra_context = {
        "title": "Sign in to your account",
        "google_oauth_client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
    }


class Logout(LogoutView, LoginRequired):
    template_name = "logout.html"


class Register(RegistrationView):
    template_name = "register.html"
    success_url = "/"
    extra_context = {"title": "Create an account"}
