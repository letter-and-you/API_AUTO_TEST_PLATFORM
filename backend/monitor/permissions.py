'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 15:04:53
LastEditors: letterzhou
LastEditTime: 2025-12-13 23:28:13
'''
from rest_framework import permissions

class IsMonitorRuleOwner(permissions.BasePermission):
    """
    监控规则权限控制
    - 项目创建者：完全控制
    - 项目管理员：可创建/编辑/删除规则
    - 普通成员：仅可查看
    """
    def has_object_permission(self, request, view, obj):
        project = obj.project
        
        # 项目创建者拥有全部权限
        if project.created_by == request.user:
            return True
            
        member = project.members.filter(user=request.user).first()
        if not member:
            return False
            
        # 管理员可编辑，普通成员仅可查看
        if request.method in permissions.SAFE_METHODS:
            return True
        return member.role == 'admin'


class CanViewAlarmLogs(permissions.BasePermission):
    """告警日志查看权限"""
    def has_object_permission(self, request, view, obj):
        # 从告警日志追溯到项目
        project = obj.record.rule.project
        # 修复：添加对公开项目的判断
        return (
            project.created_by == request.user or 
            project.members.filter(user=request.user).exists() or
            (project.is_public and request.user.is_authenticated)
        )