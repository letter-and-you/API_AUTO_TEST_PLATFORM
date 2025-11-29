'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 19:09:54
LastEditors: letterzhou
LastEditTime: 2025-11-25 19:10:00
'''
from rest_framework import permissions
from backend.machines.models import MachineMonitorData, TestMachine

class IsMachineOwnerOrAdmin(permissions.BasePermission):
    """
    仅允许机器创建者或管理员访问
    """
    def has_object_permission(self, request, view, obj):
        # 管理员拥有所有权限
        if request.user.is_staff:
            return True
        
        # 处理TestMachine对象
        if isinstance(obj, TestMachine):
            return obj.created_by == request.user
        
        # 处理MachineMonitorData对象（检查关联的机器）
        if isinstance(obj, MachineMonitorData):
            return obj.machine.created_by == request.user
        
        return False