from django.urls import path
from .views import (
    MilkRecordAPIView,
    ProductionCallBack
)

urlpatterns = [
    path("milk-records/", MilkRecordAPIView.as_view(),
         name="milk-record-list-create"),
    path("milk-records/<uuid:pk>/", MilkRecordAPIView.as_view(),
         name="milk-record-update"),
    path("milk-records/callback-url", ProductionCallBack.as_view(),
         name="production-callback"),   
]
