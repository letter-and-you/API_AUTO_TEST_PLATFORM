'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 19:12:53
LastEditors: letterzhou
LastEditTime: 2025-11-25 19:13:01
'''
from rest_framework import permissions

class IsAPIInterfaceOwnerOrProjectMember(permissions.BasePermission):
    """
    仅允许API接口创建者或所属项目成员访问
    """
    def has_object_permission(self, request, view, obj):
        # 创建者拥有所有权限
        if obj.created_by == request.user:
            return True
        
        # 项目成员拥有访问权限
        from projects.models import ProjectMember
        return ProjectMember.objects.filter(
            project=obj.project,
            user=request.user
        ).exists()