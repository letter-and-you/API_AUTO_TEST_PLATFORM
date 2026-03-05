#权限控制

from rest_framework import permissions

class IsProjectOwnerOrAdmin(permissions.BasePermission):
    """
    项目所有者或管理员权限
    允许项目创建者和管理员执行修改、删除操作
    """
    def has_object_permission(self, request, view, obj):
        # 读取权限允许所有已认证用户（如果项目公开或用户是成员）
        if request.method in permissions.SAFE_METHODS:
            return obj.is_public or obj.created_by == request.user or obj.members.filter(user=request.user).exists()
        
        # 写入权限仅允许项目创建者
        return obj.created_by == request.user

class IsProjectMember(permissions.BasePermission):
    """
    项目成员权限
    允许项目成员执行查看、执行等操作
    """
    def has_object_permission(self, request, view, obj):
        # 项目创建者拥有所有权限
        if obj.created_by == request.user:
            return True
        # 项目成员拥有读取权限
        if request.method in permissions.SAFE_METHODS:
            return obj.members.filter(user=request.user).exists()
        # 管理员成员拥有写入权限
        return obj.members.filter(user=request.user, role='admin').exists()