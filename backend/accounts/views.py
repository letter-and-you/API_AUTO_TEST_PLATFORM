# Create your views here.

from rest_framework import viewsets, status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
import base64
from .models import UserNotifyConfig
from .serializers import (
    UserRegistrationSerializer, UserSerializer, UserNotifyConfigSerializer,
    PasswordResetRequestSerializer, PasswordResetConfirmSerializer
)

User = get_user_model()

# 用户注册视图
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def user_registration(request):
    """
    用户注册接口
    请求体: email, password, password_confirm, first_name, last_name, phone
    返回：注册成功的用户信息（不含密码）
    """
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response(
            UserSerializer(user).data,
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 用户信息视图集
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    用户信息管理接口
    支持：获取当前用户信息、更新用户信息
    权限：仅登录用户可访问自己的信息
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    # 仅返回当前登录用户的信息
    def get_queryset(self):
        return User.objects.filter(id=self.request.user.id)

    # 重写retrieve方法，获取当前用户信息
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_queryset().first()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    # 添加更新用户信息的方法
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_user(request):
    user = request.user
    serializer = UserSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 通知配置视图
@api_view(['GET', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def notify_config(request):
    """
    获取/更新用户的通知配置
    GET：获取当前用户的通知配置
    PATCH：更新通知配置
    """
    config, created = UserNotifyConfig.objects.get_or_create(user=request.user)
    if request.method == 'GET':
        serializer = UserNotifyConfigSerializer(config)
        return Response(serializer.data)
    elif request.method == 'PATCH':
        serializer = UserNotifyConfigSerializer(config, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

#生成带时间戳的密码重置令牌
class ExpiringPasswordResetTokenGenerator(PasswordResetTokenGenerator):
    def check_token(self, user, token):
        # 先调用父类方法验证令牌基础有效性
        if not super().check_token(user, token):
            return False
        # 验证令牌生成时间（1小时内有效）
        # 从令牌中提取时间戳（Django默认令牌包含时间信息）
        try:
            # 解析Django内置令牌的时间戳部分
            ts_b36 = token.split('-')[0]
            timestamp = int(ts_b36, 36)
            token_time = timezone.datetime.fromtimestamp(timestamp, tz=timezone.utc)
            return token_time >= timezone.now() - timedelta(hours=1)
        except (IndexError, ValueError):
            return False
# 密码重置请求视图
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_request(request):
    """
    密码重置请求接口
    接收邮箱，发送重置链接到该邮箱
    """
    serializer = PasswordResetRequestSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        try:
            user = User.objects.get(email=email)
            # 使用自定义的带过期时间的令牌生成器
            token_generator = ExpiringPasswordResetTokenGenerator()
            token = token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
            # 发送邮件（保持原逻辑）
            send_mail(
                subject="API测试平台 - 密码重置",
                message=f"请点击链接重置密码：{reset_url}\n链接有效期为1小时",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            return Response({"message": "重置密码邮件已发送"})
        except User.DoesNotExist:
            return Response({"message": "重置密码邮件已发送"})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 密码重置确认视图
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def password_reset_confirm(request):
    """
    密码重置确认接口
    接收uid、token和新密码，验证通过后更新密码
    """
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if serializer.is_valid():
        uid = serializer.validated_data['token'].split('&')[0].split('=')[1] if '&' in serializer.validated_data['token'] else serializer.validated_data['token']
        token = serializer.validated_data['token'].split('&')[1].split('=')[1] if '&' in serializer.validated_data['token'] else ''
        new_password = serializer.validated_data['new_password']
        
        try:
            # 解码uid获取用户ID
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
            # 验证令牌
            token_generator = PasswordResetTokenGenerator()
            if token_generator.check_token(user, token):
                # 更新密码
                user.set_password(new_password)
                user.save()
                return Response({"message": "密码重置成功"})
            else:
                return Response({"error": "令牌无效或已过期"}, status=status.HTTP_400_BAD_REQUEST)
        except (User.DoesNotExist, ValueError):
            return Response({"error": "用户不存在或UID无效"}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)