from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    user_registration, UserViewSet, update_user, notify_config,
    password_reset_request, password_reset_confirm
)

router = DefaultRouter()
router.register(r'profile', UserViewSet, basename='user-profile')

urlpatterns = [
    path('register/', user_registration, name='user-register'),  # 注册
    path('profile/update/', update_user, name='user-update'),    # 更新用户信息
    path('notify-config/', notify_config, name='notify-config'),# 通知配置
    path('password-reset/', password_reset_request, name='password-reset-request'),  # 密码重置请求
    path('password-reset/confirm/', password_reset_confirm, name='password-reset-confirm'),  # 密码重置确认
] + router.urls


