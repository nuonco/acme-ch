from django.urls import path
from . import views

urlpatterns = [
    path("approve-step", views.ApproveStepView.as_view(), name="approve-step"),
]
