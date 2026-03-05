from django.db import models
from projects.models import Project
from testcases.models import TestCase, TestSuite
from machines.models import TestMachine
from django.conf import settings

class PerformanceTest(models.Model):
    """性能测试任务模型"""
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    ]
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='performance_tests',
        verbose_name='所属项目'
    )
    task_id = models.CharField(max_length=255, blank=True, null=True, verbose_name='任务ID')
    name = models.CharField(max_length=200, verbose_name='测试名称')
    description = models.TextField(blank=True, null=True, verbose_name='测试描述')
    
    # 测试目标
    test_type = models.CharField(
        max_length=20,
        choices=[('case', '单测试用例'), ('suite', '测试套件')],
        default='case',
        verbose_name='测试类型'
    )
    test_case = models.ForeignKey(
        TestCase,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performance_tests',
        verbose_name='测试用例'
    )
    test_suite = models.ForeignKey(
        TestSuite,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performance_tests',
        verbose_name='测试套件'
    )
    
    # 性能参数配置
    concurrency = models.IntegerField(default=10, verbose_name='并发用户数')
    duration = models.IntegerField(default=60, verbose_name='测试持续时间(秒)')
    ramp_up = models.IntegerField(default=0, verbose_name='逐步增加并发时间(秒)')
    loop_count = models.IntegerField(default=1, verbose_name='循环次数，0表示无限循环')
    timeout = models.IntegerField(default=30, verbose_name='请求超时时间(秒)')
    
    # 执行配置
    machine = models.ForeignKey(
        TestMachine,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performance_tests',
        verbose_name='执行机器'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='测试状态')
    
    # 关联信息
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_performance_tests',
        verbose_name='创建人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    started_at = models.DateTimeField(blank=True, null=True, verbose_name='开始时间')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='完成时间')
    
    # 性能测试报告关联
    report = models.ForeignKey(
        'reports.TestReport',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='performance_tests',
        verbose_name='关联报告'
    )
    
    
    class Meta:
        verbose_name = '性能测试'
        verbose_name_plural = '性能测试'
        db_table = 'performance_tests'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class PerformanceMetric(models.Model):
    """性能测试指标数据"""
    performance_test = models.ForeignKey(
        PerformanceTest,
        on_delete=models.CASCADE,
        related_name='metrics',
        verbose_name='所属性能测试'
    )
    timestamp = models.DateTimeField(verbose_name='记录时间')
    
    # 关键性能指标
    tps = models.FloatField(verbose_name='每秒事务数(TPS)')
    avg_response_time = models.FloatField(verbose_name='平均响应时间(毫秒)')
    min_response_time = models.FloatField(verbose_name='最小响应时间(毫秒)')
    max_response_time = models.FloatField(verbose_name='最大响应时间(毫秒)')
    p90_response_time = models.FloatField(verbose_name='90%响应时间(毫秒)')
    p95_response_time = models.FloatField(verbose_name='95%响应时间(毫秒)')
    p99_response_time = models.FloatField(verbose_name='99%响应时间(毫秒)')
    error_rate = models.FloatField(verbose_name='错误率(%)')
    concurrent_users = models.IntegerField(verbose_name='并发用户数')
    
    # 新增网络相关指标
    avg_bytes_sent = models.FloatField(default=0, verbose_name='平均发送字节数')
    avg_bytes_received = models.FloatField(default=0, verbose_name='平均接收字节数')
    network_latency = models.FloatField(default=0, verbose_name='网络延迟(毫秒)')
    
    # 新增服务器资源指标
    cpu_usage = models.FloatField(default=0, verbose_name='CPU使用率(%)')
    memory_usage = models.FloatField(default=0, verbose_name='内存使用率(%)')
    disk_io = models.FloatField(default=0, verbose_name='磁盘IO(MB/s)')
    
    class Meta:
        verbose_name = '性能指标'
        verbose_name_plural = '性能指标'
        db_table = 'performance_metrics'
        ordering = ['performance_test', 'timestamp']