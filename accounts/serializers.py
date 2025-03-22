from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    avatar = serializers.ImageField(required=False)  # Позволяет загружать файл; не обязательное поле

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'password', 'avatar', 'bio')

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user
