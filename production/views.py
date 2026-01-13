from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .permissions import IsSystemUser
from rest_framework import status
from accounts.models import Account, User, Farm, Cow
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken

# Create your views here.
class MilkRecordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Logic to create a milk record
        return Response(
            {"detail": "Milk record created successfully"},
            status=status.HTTP_201_CREATED,
        )
    