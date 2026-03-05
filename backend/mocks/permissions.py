'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 19:29:02
LastEditors: letterzhou
LastEditTime: 2025-11-25 20:25:15
'''

from rest_framework import permissions
from projects.permissions import IsProjectMember

class IsMockServiceOwnerOrProjectMember(permissions.BasePermission):
    """
    Mock服务权限控制
    - 读取权限：项目成员或公开项目
    - 写入权限：服务创建者或项目管理员
    """
    def has_object_permission(self, request, view, obj):
        # 先验证项目级权限（兼容MockService和MockResponse）
        if hasattr(obj, 'project'):
            project = obj.project
        elif hasattr(obj, 'mock_service'):
            project = obj.mock_service.project
        else:
            return False

        # 项目创建者拥有全部权限
        if project.created_by == request.user:
            return True

        # 检查是否为项目成员
        project_perm = IsProjectMember()
        if not project_perm.has_object_permission(request, view, project):
            return False

        # 读取权限允许所有项目成员
        if request.method in permissions.SAFE_METHODS:
            return True

        # 写入权限：服务创建者或项目管理员
        if hasattr(obj, 'created_by'):
            creator = obj.created_by
        elif hasattr(obj, 'mock_service'):
            creator = obj.mock_service.created_by
        else:
            creator = None

        # 项目管理员或创建者可执行写入操作
        return (
            creator == request.user or 
            project.members.filter(user=request.user, role='admin').exists()
        )