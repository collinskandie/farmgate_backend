from django.urls import path
from .views import (
    CreateMilkRecordAPIView,
)

urlpatterns = [
    path("milk-records//", MilkRecordAPIView.as_view()),
    
]
