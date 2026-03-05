'''
Author: letterzhou
Description: -- 
Date: 2025-10-25 15:04:38
LastEditors: letterzhou
LastEditTime: 2025-11-25 00:06:13
'''

# Create your models here.

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

# 项目模型
class Project(models.Model):
    """
    测试项目模型
    每个项目包含多个测试用例，由用户创建并管理
    """
    name = models.CharField(max_length=100, verbose_name='项目名称')
    description = models.TextField(blank=True, null=True, verbose_name='项目描述')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='created_projects',
        verbose_name='创建人'
    )
    is_public = models.BooleanField(default=False, verbose_name='是否公开')  # 公开项目团队成员可访问
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '项目'
        verbose_name_plural = '项目'
        db_table = 'test_projects'
        ordering = ['-created_at']
        # 同一用户的项目名称不能重复
        unique_together = ['created_by', 'name']

    def __str__(self):
        return f"{self.name} ({self.created_by.email})"

    # 统计项目相关数据的方法
    @property
    def case_count(self):
        """获取项目下的测试用例数量"""
        return self.test_cases.count()

    @property
    def last_test_time(self):
        """获取项目最后一次测试时间"""
        from reports.models import TestReport
        last_report = TestReport.objects.filter(project=self).order_by('-executed_at').first()
        return last_report.executed_at if last_report else None

    @property
    def success_rate(self):
        """获取项目最近测试的通过率"""
        from reports.models import TestReport
        last_report = TestReport.objects.filter(project=self).order_by('-executed_at').first()
        return last_report.success_rate if last_report else 0

# 项目成员模型（用于团队协作）
class ProjectMember(models.Model):
    """
    项目成员模型
    管理项目的访问权限，支持不同角色（管理员、普通成员）
    """
    ROLE_CHOICES = [
        ('admin', '管理员'),  # 可编辑项目、管理成员
        ('member', '普通成员'),  # 可查看和执行用例，不可修改项目信息
    ]
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='members',
        verbose_name='项目'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='joined_projects',
        verbose_name='成员'
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='member', verbose_name='角色')
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='加入时间')

    class Meta:
        verbose_name = '项目成员'
        verbose_name_plural = '项目成员'
        db_table = 'test_project_members'
        unique_together = ['project', 'user']  # 一个用户在一个项目中只能有一个角色

    def __str__(self):
        return f"{self.user.email} - {self.project.name} ({self.get_role_display()})"