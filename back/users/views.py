from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken


@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get("email", "").strip()
    password = request.data.get("password", "")

    if not email or not password:
        return Response(
            {"error": "Email e senha são obrigatórios."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response(
            {"error": "Credenciais inválidas."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    user = authenticate(request, username=user.username, password=password)
    if user is None:
        return Response(
            {"error": "Credenciais inválidas."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    refresh = RefreshToken.for_user(user)
    return Response(
        {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.get_full_name() or user.username,
            },
        }
    )
