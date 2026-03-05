'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 17:21:37
LastEditors: letterzhou
LastEditTime: 2025-11-25 17:21:44
'''
# reports/permissions.py
from rest_framework import permissions

class IsReportOwnerOrProjectMember(permissions.BasePermission):
    """
    允许报告的创建者或报告所属项目的成员访问。
    """
    def has_object_permission(self, request, view, obj):
        # 报告的创建者可以访问
        if obj.created_by == request.user:
            return True
        # 报告所属项目的成员可以访问
        return request.user.project_members.filter(
            project=obj.project,
            is_active=True
        ).exists()