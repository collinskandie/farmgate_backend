from rest_framework import serializers
from accounts.models import User, Account,  Farm, User, Cow


class AccountCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = [
            "id",
            "account_type",
            "name",
            "national_id",
            "company_reg_no",
            "phone",
            "email",
        ]


class FarmUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "password", "role", "full_name",
                  "phone", "national_id", "role_title"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        email = validated_data.pop("email")  # 👈 POP IT

        user = User(
            email=email,
            **validated_data
        )
        user.set_password(password)
        user.save()
        return user


class SystemUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "password", "role", "full_name",
                  "phone", "national_id", "role_title"]

    def create(self, validated_data):
        password = validated_data.pop("password")
        email = validated_data["email"]

        user = User(
            email=email,   # 🔥 same trick
            role=validated_data["role"],
            is_staff=True,
            is_superuser=True,
        )
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.CharField()
    password = serializers.CharField(write_only=True)


class CowSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cow
        fields = [
            "id",
            "name",
            "tag_number",
            "breed",
            "date_of_birth",
            # "health_status",
            "created_at",
        ]


class FarmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = [
            "id",
            "name",
            "location",
            "size_in_acres",
            "created_at",
        ]


class AccountUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "full_name",
            "email",
            "phone",
            "role",
            "role_title",
            "is_active",
        ]


class AccountDetailsSerializer(serializers.ModelSerializer):
    farms = FarmSerializer(many=True, read_only=True)
    users = AccountUserSerializer(many=True, read_only=True)

    class Meta:
        model = Account
        fields = [
            "id",
            "name",
            "account_type",
            "national_id",
            "company_reg_no",
            "location",
            "phone",
            "email",
            "is_active",
            "created_at",
            "farms",
            "users",
        ]


class FarmCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = Farm
        fields = [
            "id",
            "name",
            "location",
            "size_in_acres",

        ]


class FarmDetailsSerializer(serializers.ModelSerializer):
    cows = CowSerializer(many=True, read_only=True)

    class Meta:
        model = Farm
        fields = [
            "id",
            "name",
            "location",
            "size_in_acres",
            "created_at",
            "cows",
        ]


class CowCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cow
        fields = [
            "id",
            "tag_number",
            "breed",
            "date_of_birth",
            "is_pregnant",
            "name",

        ]
