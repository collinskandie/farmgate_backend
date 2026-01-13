from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .permissions import IsSystemUser
from rest_framework import status
from .models import Account, User, Farm, Cow
from .serializers import FarmSerializer, FarmDetailsSerializer, CowCreateSerializer
from .serializers import FarmUserCreateSerializer, AccountCreateSerializer, SystemUserCreateSerializer, LoginSerializer, AccountDetailsSerializer, FarmCreateSerializer
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404

class CreateFarmUserAPIView(APIView):
    # permission_classes = [IsAuthenticated]

    def post(self, request, account_id):
        user = request.user

        # 🔒 Only system admin or account owner
        if not (
            user.is_system_user()
            or user.account_id == account_id
        ):
            return Response(
                {"detail": "Not allowed"},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            account = Account.objects.get(id=account_id)
        except Account.DoesNotExist:
            return Response(
                {"detail": "Account not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = FarmUserCreateSerializer(data=request.data)
        if serializer.is_valid():
            new_user = serializer.save(account=account)

            return Response(
                {
                    "id": new_user.id,
                    "full_name": new_user.full_name,
                    "role": new_user.role,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class CreateFarmAPIView(APIView):
    """
    Create a farm under a specific account
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, account_id):
        user = request.user

        # 🔒 Only system users or account owners/managers
        if not user.is_system_user() and user.account_id != account_id:
            return Response(
                {"detail": "Not allowed"},
                status=status.HTTP_403_FORBIDDEN,
            )

        account = get_object_or_404(Account, id=account_id)

        serializer = FarmCreateSerializer(data=request.data)

        if serializer.is_valid():
            farm = serializer.save(account=account)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class CreateAccountAPIView(APIView):
    """
    Create Farmer / Company (Account)
    """

    permission_classes = [IsAuthenticated, IsSystemUser]

    def post(self, request):
        serializer = AccountCreateSerializer(data=request.data)

        if serializer.is_valid():
            account = serializer.save()

            return Response(
                {
                    "id": account.id,
                    "name": account.name,
                    "account_type": account.account_type,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class CreateSystemUserAPIView(APIView):
    """
    Create a system owner / system admin user
    """

    # permission_classes = [IsAuthenticated, IsSystemUser]

    def post(self, request):
        serializer = SystemUserCreateSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()

            return Response(
                {
                    "id": user.id,
                    "full_name": user.full_name,
                    "role": user.role,
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(
            serializer.errors,
            status=status.HTTP_400_BAD_REQUEST,
        )


class LoginAPIView(APIView):
    """
    Login and return JWT tokens
    """

    authentication_classes = []  # 👈 allow login without token
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        user = authenticate(username=email, password=password)

        if not user:
            return Response(
                {"detail": "Invalid credentials"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.is_active:
            return Response(
                {"detail": "User account is disabled"},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh = RefreshToken.for_user(user)
        #get user details
        user_details  = User.objects.get(id=user.id)

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "full_name": user_details.full_name,
                    "email": user_details.email,
                    "role": user.role,
                    "role_title": user_details.role_title,
                    "account_id": user.account_id,
                },
            },
            status=status.HTTP_200_OK,
        )


class AccountListAPIView(APIView):
    """
    List all farms (accounts of type 'farmer' or 'company')
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # 🔒 Only system users can view all farms
        if not user.is_system_user():
            return Response(
                {"detail": "Not allowed"},
                status=status.HTTP_403_FORBIDDEN,
            )

        farms = Account.objects.all()
        farm_list = [
            {
                "id": farm.id,
                "name": farm.name,
                "account_type": farm.account_type,
                "phone": farm.phone,
                "email": farm.email,
            }
            for farm in farms
        ]

        return Response(farm_list, status=status.HTTP_200_OK)


class AccountDetailsAPIView(APIView):
    """
    Retrieve full account details:
    - Account info
    - Farms under the account
    - Users (employees) under the account
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, account_id):
        user = request.user

        # 🔒 Only system users can view ANY account
        if not user.is_system_user():
            return Response(
                {"detail": "Not allowed"},
                status=status.HTTP_403_FORBIDDEN,
            )

        account = get_object_or_404(
            Account.objects.prefetch_related("farms", "users"),
            id=account_id,
        )

        serializer = AccountDetailsSerializer(account)

        return Response(serializer.data, status=status.HTTP_200_OK)


class FarmDetailsAPIView(APIView):
    """
    Retrieve details of a specific farm
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, farm_id):
        user = request.user

        # 🔒 Only system users can view ANY farm
        if not user.is_system_user():
            return Response(
                {"detail": "Not allowed"},
                status=status.HTTP_403_FORBIDDEN,
            )

        farm = get_object_or_404(
            Farm,
            id=farm_id,
        )

        serializer = FarmDetailsSerializer(farm)

        return Response(serializer.data, status=status.HTTP_200_OK)

class CreateCowAPIView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user

        cows = Cow.objects.select_related("farm").all()
        cow_list = [
            {
                "id": cow.id,
                "name": cow.name,
                "tag_number": cow.tag_number,
                "breed": cow.breed,
                "date_of_birth": cow.date_of_birth,
                "farm": {
                    "id": cow.farm.id,
                    "name": cow.farm.name,
                },
            }
            for cow in cows
        ]

        return Response(cow_list, status=status.HTTP_200_OK)

    def post(self, request, farm_id):
        user = request.user

        farm = get_object_or_404(Farm, id=farm_id)

        # 🔒 Permissions: system admin or farm account user
        if not (
            user.is_system_user()
            or user.account_id == farm.account_id
        ):
            return Response(
                {"detail": "Not allowed"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CowCreateSerializer(data=request.data)
        if serializer.is_valid():
            cow = serializer.save(farm=farm)
            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
