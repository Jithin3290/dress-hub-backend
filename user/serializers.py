# accounts/serializers.py
from rest_framework import serializers
from .models import User
from rest_framework import serializers
import re
from django.core.validators import validate_email as django_validate_email
from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import serializers
from django.core.validators import validate_email as django_validate_email
from django.core.exceptions import ValidationError as DjangoValidationError
import re

class SignupSerializer(serializers.ModelSerializer):
    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    profile_picture = serializers.ImageField(required=False)

    class Meta:
        model = User
        fields = [
            "email",
            "name",
            "phone_number",
            "profile_picture",
            "password1",
            "password2",
        ]

    # ----------------------------
    # EMAIL VALIDATION (format + uniqueness)
    # ----------------------------
    def validate_email(self, value):
        # Format validation
        try:
            django_validate_email(value)
        except DjangoValidationError:
            raise serializers.ValidationError("Enter a valid email address")

        # Uniqueness
        qs = User.objects.filter(email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Email already exists")

        return value

    # ----------------------------
    #  PHONE VALIDATION (regex + uniqueness)
    # ----------------------------
    def validate_phone_number(self, value):
        # want international  r"^\+?[1-9]\d{7,14}$"
        phone_regex = r"^[6-9]\d{9}$"

        if not re.match(phone_regex, value):
            raise serializers.ValidationError(
                "Enter a valid indian phone number"
            )

        # Uniqueness check
        qs = User.objects.filter(phone_number=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Phone number already exists")

        return value

    # ----------------------------
    # PASSWORD MATCH VALIDATION
    # ----------------------------
    def validate(self, attrs):
        if attrs["password1"] != attrs["password2"]:
            raise serializers.ValidationError("Passwords do not match")
        return attrs

    # ----------------------------
    # CREATE USER
    # ----------------------------
    def create(self, validated_data):
        password = validated_data.pop("password1")
        validated_data.pop("password2")

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user



class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "phone_number",
            "profile_picture",
            "is_banned",
        ]


class ProfileSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "name",
            "phone_number",
            "profile_picture",
            "is_banned",
        ]
        read_only_fields = ["id", "email"]

    def validate_email(self, value):
        qs = User.objects.filter(email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate_phone_number(self, value):
        qs = User.objects.filter(phone_number=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Phone number already exists")
        return value

    def to_representation(self, instance):
        """
        Ensure profile_picture is an absolute URL when the serializer has 'request' in context.
        """
        data = super().to_representation(instance)
        request = self.context.get("request", None)
        pic = data.get("profile_picture")
        if pic and request and pic.startswith("/"):
            data["profile_picture"] = request.build_absolute_uri(pic)
        return data
