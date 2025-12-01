"""
URL configuration for acme_ch project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from django.conf.urls import include
from common.views import livez

urlpatterns = [
    path("livez", livez, name="livez"),
    path("admin/", admin.site.urls),
    # Auth
    # django registraion
    # TODO(fd): remove in favor of google auth
    # path("accounts/", include("django_registration.backends.one_step.urls")),
    # auth urls
    path("accounts/", include("django.contrib.auth.urls")),
    # allauth urls
    path("accounts/", include("allauth.urls")),
    # authorization
    path("auth/", include("authorization.urls")),
    # API endpoints
    path("api/orgs/", include("organizations.urls")),
    path("api/nuon-proxy/", include("nuon_proxy.urls")),
    # Dashboard (HTML views)
    path("", include("dashboard.urls")),
]
