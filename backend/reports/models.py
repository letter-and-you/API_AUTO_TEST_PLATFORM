# reports/models.py
import uuid
from django.db import models
from django.conf import settings
from projects.models import Project
from testcases.models import TestCase, TestSuite

class TestReport(models.Model):
    """测试报告模型"""
    REPORT_TYPE_CHOICES = [
        ('suite', '套件测试'),
        ('case', '单例测试'),
    ]
    STATUS_CHOICES = [
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '执行失败'), # 指整个报告生成过程失败
    ]

    # 基本信息
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, verbose_name='报告ID')
    name = models.CharField(max_length=200, verbose_name='报告名称')
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='test_reports',
        verbose_name='所属项目'
    )
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, verbose_name='报告类型')
    
    # 关联测试对象
    test_suite = models.ForeignKey(
        TestSuite,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports',
        verbose_name='关联套件'
    )
    test_case = models.ForeignKey(
        TestCase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports',
        verbose_name='关联用例'
    )

    # 执行概要统计
    total_cases = models.IntegerField(default=0, verbose_name='总用例数')
    passed_cases = models.IntegerField(default=0, verbose_name='通过用例数')
    failed_cases = models.IntegerField(default=0, verbose_name='失败用例数')
    skipped_cases = models.IntegerField(default=0, verbose_name='跳过用例数')
    success_rate = models.FloatField(default=0.0, verbose_name='通过率(%)')
    total_duration = models.FloatField(default=0.0, verbose_name='总耗时(秒)')
    average_response_time = models.FloatField(default=0.0, verbose_name='平均响应时间(毫秒)')

    # 状态与时间
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running', verbose_name='状态')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_reports',
        verbose_name='创建人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')     # 报告开始执行时间
    executed_at = models.DateTimeField(blank=True, null=True, verbose_name='执行时间')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='完成时间')

    # 报告文件
    html_report_file = models.FileField(upload_to='reports/html/', blank=True, null=True, verbose_name='HTML报告文件')

    class Meta:
        verbose_name = '测试报告'
        verbose_name_plural = '测试报告'
        db_table = 'test_reports'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_report_type_display()})"

class TestResult(models.Model):
    """用例执行结果模型"""
    STATUS_CHOICES = [
        ('passed', '通过'),
        ('failed', '失败'),
        ('skipped', '跳过'),
    ]

    test_report = models.ForeignKey(
        TestReport,
        on_delete=models.CASCADE,
        related_name='test_results',
        verbose_name='所属报告'
    )
    test_case = models.ForeignKey(
        TestCase,
        on_delete=models.CASCADE,
        related_name='test_results',
        verbose_name='测试用例'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='skipped', verbose_name='执行状态')
    duration = models.FloatField(default=0.0, verbose_name='耗时(秒)')
    executed_at = models.DateTimeField(auto_now_add=True, verbose_name='执行时间')

    # 请求数据
    request_headers = models.JSONField(default=dict, blank=True, verbose_name='请求头')
    request_method = models.CharField(max_length=10, blank=True, verbose_name='请求方法')
    request_url = models.URLField(blank=True, verbose_name='请求URL')
    request_params = models.JSONField(default=dict, blank=True, verbose_name='请求参数(URL)')
    request_body = models.TextField(blank=True, null=True, verbose_name='请求体')

    # 响应数据
    response_status_code = models.IntegerField(blank=True, null=True, verbose_name='响应状态码')
    response_headers = models.JSONField(default=dict, blank=True, verbose_name='响应头')
    response_body = models.TextField(blank=True, null=True, verbose_name='响应体')

    # 失败信息
    error_message = models.TextField(blank=True, null=True, verbose_name='错误信息')
    failure_details = models.JSONField(default=list, blank=True, verbose_name='失败详情') # 存储断言失败等明细

    class Meta:
        verbose_name = '用例执行结果'
        verbose_name_plural = '用例执行结果'
        db_table = 'test_results'
        ordering = ['executed_at']

    def __str__(self):
        return f"{self.test_case.name} - {self.get_status_display()}"