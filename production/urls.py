from django.urls import path
from .views import (
    MilkRecordAPIView,
    ProductionCallBack,
    MilkBulkRecordAPIView
)

urlpatterns = [
    path("milk-records/", MilkRecordAPIView.as_view(),
         name="milk-record-list-create"),
    path("milk-records/<uuid:pk>/", MilkRecordAPIView.as_view(),
         name="milk-record-update"),
    path("milk-records/callback-url", ProductionCallBack.as_view(),
         name="production-callback"),
    path("milk-records/bulk/", MilkBulkRecordAPIView.as_view(),
         name="milk-record-bulk-create"),
]
