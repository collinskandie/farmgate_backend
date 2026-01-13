from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid


class Account(models.Model):
    """
    Tenant model.
    Represents a Farmer or Company.
    """

    INDIVIDUAL = "individual"
    COMPANY = "company"

    ACCOUNT_TYPE_CHOICES = [
        (INDIVIDUAL, "Individual"),
        (COMPANY, "Company"),
    ]

    account_type = models.CharField(
        max_length=20, choices=ACCOUNT_TYPE_CHOICES
    )

    name = models.CharField(max_length=255)
    national_id = models.CharField(max_length=50, blank=True, null=True)
    company_reg_no = models.CharField(max_length=50, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Farm(models.Model):
    """
    Represents farms owned by accounts.
    """

    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="farms",
    )
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    size_in_acres = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.account.name})"


class User(AbstractUser):
    """
    System users and tenant employees.
    """

    SYSTEM_OWNER = "system_owner"
    SYSTEM_ADMIN = "system_admin"
    ACCOUNT_OWNER = "account_owner"
    MANAGER = "manager"
    EMPLOYEE = "employee"

    ROLE_CHOICES = [
        (SYSTEM_OWNER, "System Owner"),
        (SYSTEM_ADMIN, "System Admin"),
        (ACCOUNT_OWNER, "Account Owner"),
        (MANAGER, "Manager"),
        (EMPLOYEE, "Employee"),
    ]
    username = None  # 👈 email-only auth
    email = models.EmailField(unique=True)

    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES
    )

    # Tenant scope (null = system user)
    account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )

    # Farm assignments
    farms = models.ManyToManyField(
        Farm,
        blank=True,
        related_name="users",
    )

    # Employee profile fields
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    national_id = models.CharField(max_length=50, blank=True, null=True)
    role_title = models.CharField(max_length=100, blank=True)

    is_account_active = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def is_system_user(self):
        return self.role in {self.SYSTEM_OWNER, self.SYSTEM_ADMIN}

    def is_tenant_user(self):
        return self.account_id is not None

    def __str__(self):
        return self.email

class Cow(models.Model):
    """
    Represents a cow in the farm.
    """
    name = models.CharField(max_length=255)
    farm = models.ForeignKey(
        Farm,
        on_delete=models.CASCADE,
        related_name="cows",
    )
    tag_number = models.CharField(max_length=50, unique=True)
    breed = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    is_pregnant = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cow {self.tag_number} ({self.farm.name})"