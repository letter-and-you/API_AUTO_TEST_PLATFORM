# Create your models here.
# 执行器模型，管理测试任务的执行节点
from django.db import models
from django.conf import settings
from projects.models import Project

class Executor(models.Model):
    """执行器模型，管理测试任务的执行节点"""
    STATUS_CHOICES = [
        ('idle', '空闲'),
        ('running', '运行中'),
        ('offline', '离线'),
        ('error', '错误'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='执行器名称')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    type = models.CharField(max_length=20, choices=[('local', '本地'), ('remote', '远程')], default='local', verbose_name='类型')
    host = models.CharField(max_length=255, blank=True, null=True, verbose_name='主机地址')
    port = models.IntegerField(default=8000, blank=True, null=True, verbose_name='端口')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline', verbose_name='状态')
    max_concurrent = models.IntegerField(default=5, verbose_name='最大并发数')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='executors',
        verbose_name='创建人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '执行器'
        verbose_name_plural = '执行器'
        db_table = 'executors'
        
    def __str__(self):
        return self.name

class ExecutionQueue(models.Model):
    """执行队列，管理等待执行的测试任务"""
    TASK_TYPE_CHOICES = [
        ('test_case', '测试用例'),
        ('test_suite', '测试套件'),
        ('performance', '性能测试'),
    ]
    
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES, verbose_name='任务类型')
    task_id = models.UUIDField(verbose_name='任务ID')
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='execution_queues',
        verbose_name='所属项目'
    )
    priority = models.IntegerField(default=5, verbose_name='优先级，1-10，数字越大优先级越高')
    status = models.CharField(max_length=20, choices=[('pending', '等待中'), ('processing', '处理中'), ('completed', '已完成')], default='pending', verbose_name='状态')
    executor = models.ForeignKey(
        Executor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='queues',
        verbose_name='执行器'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='execution_queues',
        verbose_name='创建人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    started_at = models.DateTimeField(blank=True, null=True, verbose_name='开始执行时间')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='完成时间')
    
    class Meta:
        verbose_name = '执行队列'
        verbose_name_plural = '执行队列'
        db_table = 'execution_queues'
        ordering = ['-priority', 'created_at']
        
    def __str__(self):
        return f"{self.get_task_type_display()} - {self.task_id}"