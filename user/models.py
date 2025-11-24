# user/models.py
from django.db import models
from django.contrib.auth.models import (
    AbstractUser,
    BaseUserManager,
    Group,
    Permission,
)


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, name, phone_number, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        # provide sensible defaults if not passed
        name = extra_fields.pop("name", "Admin")
        phone_number = extra_fields.pop("phone_number", "0000000000")

        return self.create_user(
            email=email,
            password=password,
            name=name,
            phone_number=phone_number,
            **extra_fields,
        )


class User(AbstractUser):
    username = None
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True, default="0000000000")
    profile_picture = models.ImageField(upload_to="profiles/", default="default.png", null=True)
    is_banned = models.BooleanField(default=False)

    # override to avoid reverse accessor clashes with auth.User
    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_groups",
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_permissions",
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name", "phone_number"]

    objects = UserManager()

    def __str__(self):
        return self.email
