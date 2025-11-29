'''
Author: letterzhou
Description: -- 
Date: 2025-11-24 23:47:38
LastEditors: letterzhou
LastEditTime: 2025-11-24 23:47:48
'''

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import UserNotifyConfig

User = get_user_model()

# 用户注册序列化器
class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password], style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('email', 'password', 'password_confirm', 'first_name', 'last_name', 'phone')
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'email': {'required': True}
        }

    # 验证密码一致性
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "密码和确认密码不一致"})
        return attrs

    # 创建用户
    def create(self, validated_data):
        validated_data.pop('password_confirm')  # 移除确认密码字段
        user = User.objects.create_user(**validated_data)
        # 为用户创建默认通知配置
        UserNotifyConfig.objects.create(user=user)
        return user

# 用户信息序列化器（用于详情和更新）
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'phone', 'alarm_email', 'avatar', 'created_at')
        read_only_fields = ('id', 'created_at')
        extra_kwargs = {
            'avatar': {'required': False}
        }

# 通知配置序列化器
class UserNotifyConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotifyConfig
        fields = ('id', 'notify_type', 'is_active', 'mute_start', 'mute_end')

# 密码重置请求序列化器
class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

# 密码重置确认序列化器
class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "密码和确认密码不一致"})
        return attrs