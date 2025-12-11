from rest_framework import serializers
from user.models import User

class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "name",
            "email",
            "phone_number",
            "profile_picture",
            "is_banned",
        )
        read_only_fields = ("id",)
