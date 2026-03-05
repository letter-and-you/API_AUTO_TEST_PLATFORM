'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 16:49:08
LastEditors: letterzhou
LastEditTime: 2025-11-25 16:50:46
'''
# Create your models here.
from django.db import models
from django.conf import settings

class TestMachine(models.Model):
    """测试机器资源模型"""
    STATUS_CHOICES = [
        ('online', '在线'),
        ('offline', '离线'),
        ('busy', '忙碌'),
        ('maintenance', '维护中'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='机器名称')
    ip_address = models.GenericIPAddressField(verbose_name='IP地址')
    port = models.IntegerField(default=22, verbose_name='SSH端口')
    description = models.TextField(blank=True, null=True, verbose_name='机器描述')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='offline', verbose_name='状态')
    os = models.CharField(max_length=100, blank=True, null=True, verbose_name='操作系统')
    cpu_cores = models.IntegerField(blank=True, null=True, verbose_name='CPU核心数')
    memory = models.CharField(max_length=50, blank=True, null=True, verbose_name='内存大小')
    disk = models.CharField(max_length=50, blank=True, null=True, verbose_name='磁盘大小')
    username = models.CharField(max_length=100, verbose_name='登录用户名')
    password = models.CharField(max_length=100, blank=True, null=True, verbose_name='登录密码')
    private_key = models.TextField(blank=True, null=True, verbose_name='SSH私钥')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_machines',
        verbose_name='创建人'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    last_heartbeat = models.DateTimeField(blank=True, null=True, verbose_name='最后心跳时间')
    
    class Meta:
        verbose_name = '测试机器'
        verbose_name_plural = '测试机器'
        db_table = 'test_machines'
        ordering = ['name']
        unique_together = ['ip_address', 'port']
    
    def __str__(self):
        return f"{self.name} ({self.ip_address}:{self.port})"

class MachineMonitorData(models.Model):
    """机器监控数据"""
    machine = models.ForeignKey(
        TestMachine,
        on_delete=models.CASCADE,
        related_name='monitor_data',
        verbose_name='所属机器'
    )
    cpu_usage = models.FloatField(verbose_name='CPU使用率(%)')
    memory_usage = models.FloatField(verbose_name='内存使用率(%)')
    disk_usage = models.FloatField(verbose_name='磁盘使用率(%)')
    network_in = models.FloatField(verbose_name='网络入流量(KB/s)')
    network_out = models.FloatField(verbose_name='网络出流量(KB/s)')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='记录时间')
    
    class Meta:
        verbose_name = '机器监控数据'
        verbose_name_plural = '机器监控数据'
        db_table = 'machine_monitor_data'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.machine.name} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"