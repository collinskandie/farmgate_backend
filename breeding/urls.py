from django.urls import path
from .views import (
    BreedingDashboardAPIView
)

urlpatterns = [
    path('dashboard/<int:farm_id>/', BreedingDashboardAPIView.as_view()),
]
