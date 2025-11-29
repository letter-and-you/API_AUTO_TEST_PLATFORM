
# Create your models here.
from django.db import models
from django.conf import settings
from projects.models import Project
from testcases.models import TestCase

class MonitorRule(models.Model):
    """监控规则模型"""
    RULE_TYPE_CHOICES = [
        ('response_time', '响应时间阈值'),
        ('error_rate', '错误率阈值'),
        ('status_code', '状态码异常'),
        ('custom', '自定义断言'),
    ]
    
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE,
        related_name='monitor_rules',
        verbose_name='关联项目'
    )
    test_case = models.ForeignKey(
        TestCase, 
        on_delete=models.CASCADE,
        related_name='monitor_rules',
        null=True, blank=True,
        verbose_name='关联用例'
    )
    rule_type = models.CharField(max_length=20, choices=RULE_TYPE_CHOICES, verbose_name='规则类型')
    threshold = models.FloatField(help_text="例如：响应时间阈值(ms)、错误率(0-1)", verbose_name='阈值')
    interval = models.IntegerField(default=300, help_text="监控间隔(秒)", verbose_name='监控间隔')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_monitor_rules',
        verbose_name='创建人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '监控规则'
        verbose_name_plural = '监控规则'
        db_table = 'monitor_rules'
        unique_together = ['project', 'test_case', 'rule_type']  # 同一用例的规则类型唯一

    def __str__(self):
        return f"{self.get_rule_type_display()}:{self.threshold}({self.project.name})"


class MonitorRecord(models.Model):
    """监控记录模型"""
    STATUS_CHOICES = [
        ('normal', '正常'),
        ('warning', '警告'),
        ('critical', '严重'),
    ]
    
    rule = models.ForeignKey(
        MonitorRule,
        on_delete=models.CASCADE,
        related_name='records',
        verbose_name='关联规则'
    )
    actual_value = models.FloatField(verbose_name='实际值')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, verbose_name='状态')
    message = models.TextField(null=True, blank=True, verbose_name='描述信息')
    executed_at = models.DateTimeField(auto_now_add=True, verbose_name='监控时间')

    class Meta:
        verbose_name = '监控记录'
        verbose_name_plural = '监控记录'
        db_table = 'monitor_records'
        ordering = ['-executed_at']

    def __str__(self):
        return f"{self.rule.get_rule_type_display()} {self.status}:{self.actual_value}"


class AlarmLog(models.Model):
    """告警日志模型"""
    record = models.ForeignKey(
        MonitorRecord,
        on_delete=models.CASCADE,
        related_name='alarms',
        verbose_name='关联记录'
    )
    notified_users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='received_alarms',
        verbose_name='通知用户'
    )
    notify_type = models.CharField(max_length=10, choices=[('email', '邮件'), ('sms', '短信')], verbose_name='通知方式')
    is_success = models.BooleanField(default=True, verbose_name='是否发送成功')
    message = models.TextField(verbose_name='告警内容')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '告警日志'
        verbose_name_plural = '告警日志'
        db_table = 'alarm_logs'

    def __str__(self):
        return f"{self.get_notify_type_display()}告警：{self.record.rule.rule_type}"