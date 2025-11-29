'''
Author: letterzhou
Description: -- 
Date: 2025-11-11 19:50:11
LastEditors: letterzhou
LastEditTime: 2025-11-25 20:33:26
'''
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _

# Create your models here.  #数据库模型,表结构
# 自定义用户管理器（支持邮箱作为用户名登录）
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('The Email must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email,** extra_fields)
        user.set_password(password)  # 密码加密存储
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password,** extra_fields)

# 自定义用户模型（扩展Django默认用户）
class User(AbstractUser):
    """
    系统用户模型，使用邮箱作为登录凭证
    扩展字段：头像、告警邮箱、手机号等
    """
    username = None  # 取消用户名字段
    email = models.EmailField(_('email address'), unique=True)  # 邮箱作为唯一标识
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='头像')
    alarm_email = models.EmailField(_('alarm email'), null=True, blank=True, verbose_name='告警邮箱')
    phone = models.CharField(max_length=11, null=True, blank=True, verbose_name='手机号')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='手机号')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='头像')
    remember_me = models.BooleanField(default=False, verbose_name='记住登录状态')
    last_login_ip = models.GenericIPAddressField(blank=True, null=True, verbose_name='最后登录IP')
    
    # 指定登录字段为邮箱
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # 创建超级用户时不需要额外字段

    objects = UserManager()

    class Meta:
        verbose_name = _('用户')
        verbose_name_plural = _('用户')
        db_table = 'sys_users'  # 数据库表名

    def __str__(self):
        return self.email

# 用户通知配置模型
class UserNotifyConfig(models.Model):
    """用户的告警通知配置"""
    NOTIFY_TYPE_CHOICES = [
        ('email', '邮件'),
        ('phones', '电话'),
        ('both', '邮件和电话')
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notify_config', verbose_name='用户')
    notify_type = models.CharField(max_length=10, choices=NOTIFY_TYPE_CHOICES, default='email', verbose_name='通知方式')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    mute_start = models.TimeField(null=True, blank=True, verbose_name='静音开始时间')  # 例如：22:00
    mute_end = models.TimeField(null=True, blank=True, verbose_name='静音结束时间')    # 例如：08:00

    class Meta:
        verbose_name = '通知配置'
        verbose_name_plural = '通知配置'
        db_table = 'sys_user_notify_config'