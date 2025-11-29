'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 16:28:23
LastEditors: letterzhou
LastEditTime: 2025-11-25 16:34:16
'''
from django.db import models

# Create your models here.
from django.db import models
from projects.models import Project
from django.conf import settings

class APIInterface(models.Model):
    """API接口模型"""
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
        ('PATCH', 'PATCH'),
        ('HEAD', 'HEAD'),
        ('OPTIONS', 'OPTIONS'),
    ]
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='interfaces',
        verbose_name='所属项目'
    )
    name = models.CharField(max_length=200, verbose_name='接口名称')
    description = models.TextField(blank=True, null=True, verbose_name='接口描述')
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default='GET', verbose_name='请求方法')
    url = models.URLField(verbose_name='接口URL')
    headers = models.JSONField(default=dict, blank=True, verbose_name='默认请求头')
    query_parameters = models.JSONField(default=dict, blank=True, verbose_name='默认查询参数')
    request_example = models.TextField(blank=True, null=True, verbose_name='请求示例')
    response_example = models.TextField(blank=True, null=True, verbose_name='响应示例')
    status_code = models.IntegerField(default=200, verbose_name='默认状态码')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_interfaces',
        verbose_name='创建人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_active = models.BooleanField(default=True, verbose_name='是否有效')
    
    class Meta:
        verbose_name = 'API接口'
        verbose_name_plural = 'API接口'
        db_table = 'api_interfaces'
        ordering = ['-created_at']
        unique_together = ['project', 'name', 'method', 'url']
    
    def __str__(self):
        return f"{self.name} ({self.method} {self.url})"