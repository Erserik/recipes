from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response  # Не забудьте импортировать Response
from rest_framework import status, serializers, generics
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import UserRegistrationSerializer

class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserRegistrationSerializer
    permission_classes = []  # Регистрация доступна без авторизации

    @swagger_auto_schema(
        operation_summary="Регистрация пользователя",
        operation_description=(
            "Позволяет зарегистрироваться новому пользователю. "
            "Необходимы: email, username, password; поля avatar и bio опциональны. "
            "При успешной регистрации возвращаются данные пользователя."
        ),
        request_body=UserRegistrationSerializer,
        responses={
            201: openapi.Response(
                description="Успешная регистрация",
                examples={
                    "application/json": {
                        "id": 1,
                        "email": "user@example.com",
                        "username": "User1",
                        "avatar": "http://localhost:8000/media/avatars/filename.jpg",
                        "bio": "Люблю готовить"
                    }
                }
            ),
            400: "Ошибка валидации"
        }
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "id": user.id,
                "email": user.email,
                "username": user.username,
                # Возвращаем URL аватарки, если файл загружен
                "avatar": user.avatar.url if user.avatar else None,
                "bio": user.bio,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Получение данных текущего пользователя",
        operation_description="Возвращает информацию о текущем авторизованном пользователе.",
        responses={
            200: openapi.Response(
                description="Данные пользователя",
                examples={
                    "application/json": {
                        "id": 1,
                        "email": "user@example.com",
                        "username": "User1",
                        "avatar": "http://localhost:8000/media/avatars/filename.jpg",
                        "bio": "Люблю готовить"
                    }
                }
            ),
            401: "Неавторизованный доступ"
        }
    )
    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "avatar": user.avatar.url if user.avatar else None,
            "bio": user.bio,
        })

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=6)

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="Смена пароля пользователя",
        operation_description=(
            "Позволяет сменить пароль текущего пользователя. "
            "Требуется указать старый и новый пароли. "
            "При неправильном вводе старого пароля возвращается ошибка."
        ),
        request_body=ChangePasswordSerializer,
        responses={
            200: openapi.Response(
                description="Пароль успешно изменен",
                examples={"application/json": {"message": "Пароль успешно изменен"}}
            ),
            400: "Ошибка валидации или неверный старый пароль",
            401: "Неавторизованный доступ"
        }
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({"old_password": ["Неверный текущий пароль"]}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({"message": "Пароль успешно изменен"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
