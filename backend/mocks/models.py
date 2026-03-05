# Create your models here.
from django.db import models
from django.conf import settings
from projects.models import Project
from apis.models import APIInterface

class MockService(models.Model):
    """Mock服务模型"""
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='mock_services',
        verbose_name='所属项目'
    )
    interface = models.ForeignKey(
        APIInterface,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mock_services',
        verbose_name='关联接口'
    )
    name = models.CharField(max_length=200, verbose_name='Mock服务名称')
    description = models.TextField(blank=True, null=True, verbose_name='服务描述')
    path = models.CharField(max_length=500, verbose_name='Mock路径')
    method = models.CharField(
        max_length=10,
        choices=[('GET', 'GET'), ('POST', 'POST'), ('PUT', 'PUT'), ('DELETE', 'DELETE'), ('ALL', '所有方法')],
        default='GET',
        verbose_name='请求方法'
    )
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_mock_services',
        verbose_name='创建人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = 'Mock服务'
        verbose_name_plural = 'Mock服务'
        db_table = 'mock_services'
        ordering = ['-created_at']
        unique_together = ['project', 'path', 'method']
    
    def __str__(self):
        return f"{self.name} ({self.method} {self.path})"

class MockResponse(models.Model):
    """Mock响应配置,支持多条件返回不同结果"""
    mock_service = models.ForeignKey(
        MockService,
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name='所属Mock服务'
    )
    name = models.CharField(max_length=200, verbose_name='响应名称')
    priority = models.IntegerField(default=0, verbose_name='优先级，数字越大越优先')
    
    # 匹配条件
    match_type = models.CharField(
        max_length=20,
        choices=[('exact', '完全匹配'), ('contains', '包含'), ('regex', '正则匹配')],
        default='exact',
        verbose_name='匹配类型'
    )
    match_headers = models.JSONField(default=dict, blank=True, verbose_name='匹配请求头')
    match_params = models.JSONField(default=dict, blank=True, verbose_name='匹配查询参数')
    match_body = models.TextField(blank=True, null=True, verbose_name='匹配请求体')
    
    # 响应内容
    status_code = models.IntegerField(default=200, verbose_name='响应状态码')
    response_headers = models.JSONField(default=dict, blank=True, verbose_name='响应头')
    response_body = models.TextField(verbose_name='响应体')
    response_type = models.CharField(
        max_length=20,
        choices=[('json', 'JSON'), ('xml', 'XML'), ('text', '文本'), ('html', 'HTML')],
        default='json',
        verbose_name='响应体类型'
    )
    delay = models.IntegerField(default=0, verbose_name='响应延迟(毫秒)')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = 'Mock响应'
        verbose_name_plural = 'Mock响应'
        db_table = 'mock_responses'
        ordering = ['mock_service', '-priority']
    
    def __str__(self):
        return f"{self.mock_service.name} - {self.name}"
    def matches_request(self, headers, params, body):
        """检查请求是否匹配当前响应规则"""
        # 匹配请求头
        for key, value in self.match_headers.items():
            if headers.get(key) != value:
                return False
        
        # 匹配查询参数
        for key, value in self.match_params.items():
            if params.get(key) != value:
                return False
        
        # 匹配请求体
        if not self.match_body:
            return True  # 无匹配体条件时直接匹配
        
        if self.match_type == 'exact' and self.match_body != body:
            return False
        if self.match_type == 'contains' and self.match_body not in body:
            return False
        if self.match_type == 'regex':
            try:
                import re
                if not re.search(self.match_body, body):
                    return False
            except re.error:
                return False  # 正则表达式无效时不匹配
        
        return True