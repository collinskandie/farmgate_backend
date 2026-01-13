from django.urls import path
from .views import (
    CreateFarmUserAPIView,
    CreateAccountAPIView,
    CreateSystemUserAPIView,
    LoginAPIView,
    AccountListAPIView,
    AccountDetailsAPIView,
    CreateFarmAPIView,
    FarmDetailsAPIView,
    CreateCowAPIView,
)

urlpatterns = [
    path("create/", CreateAccountAPIView.as_view()),
    path("system-users/create/", CreateSystemUserAPIView.as_view()),
    path("login/", LoginAPIView.as_view()),
    path("list/", AccountListAPIView.as_view()),
    path("<int:account_id>/", AccountDetailsAPIView.as_view()),
    path(
        "<int:account_id>/users/create/",
        CreateFarmUserAPIView.as_view(),
        name="create-farm-user",
    ),

    path(
        "<int:account_id>/farms/create/",
        CreateFarmAPIView.as_view(),
        name="create-farm",
    ),
    path("farm/<int:farm_id>/", FarmDetailsAPIView.as_view()),
    path("getcows/", CreateCowAPIView.as_view()),
    path(
        "farm/<int:farm_id>/cows/create/",
        CreateCowAPIView.as_view(),
        name="create-cow",
    ),
]
