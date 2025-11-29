
from rest_framework import permissions
from projects.permissions import IsProjectMember

class IsTestCaseOwnerOrProjectMember(permissions.BasePermission):
    """
    测试用例权限控制
    - 读取权限：项目成员或公开项目
    - 写入权限：用例创建者或项目管理员
    """
    def has_object_permission(self, request, view, obj):
        # 先验证项目级权限
        project_perm = IsProjectMember()
        if not project_perm.has_object_permission(request, view, obj.project):
            return False
        
        # 读取权限允许所有项目成员
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # 写入权限：用例创建者或项目创建者
        return obj.created_by == request.user or obj.project.created_by == request.user

class IsTestSuiteOwnerOrProjectMember(permissions.BasePermission):
    """
    测试套件权限控制
    逻辑与测试用例权限一致
    """
    def has_object_permission(self, request, view, obj):
        project_perm = IsProjectMember()
        if not project_perm.has_object_permission(request, view, obj.project):
            return False
        
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return obj.created_by == request.user or obj.project.created_by == request.user