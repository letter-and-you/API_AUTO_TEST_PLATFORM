'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 14:46:21
LastEditors: letterzhou
LastEditTime: 2025-11-25 14:49:01
'''


from rest_framework import permissions
from projects.permissions import IsProjectMember
from testcases.models import TestCase, TestSuite

class CanExecuteTestCase(permissions.BasePermission):
    """
    测试用例执行权限
    允许项目成员执行已启用的用例
    """
    def has_permission(self, request, view):
        if request.method != 'POST':
            return True

        test_case_id = view.kwargs.get('pk') or request.data.get('test_case_id')
        if not test_case_id:
            return False

        try:
            test_case = TestCase.objects.get(id=test_case_id, is_active=True)
            # 验证项目权限和用例状态
            project_perm = IsProjectMember()
            return (
                project_perm.has_object_permission(request, view, test_case.project) and
                test_case.status == 'active'
            )
        except TestCase.DoesNotExist:
            return False

class CanExecuteTestSuite(permissions.BasePermission):
    """
    测试套件执行权限
    允许项目成员执行包含已启用用例的套件
    """
    def has_permission(self, request, view):
        if request.method != 'POST':
            return True

        test_suite_id = view.kwargs.get('pk') or request.data.get('test_suite_id')
        if not test_suite_id:
            return False

        try:
            test_suite = TestSuite.objects.get(id=test_suite_id)
            # 验证项目权限
            project_perm = IsProjectMember()
            if not project_perm.has_object_permission(request, view, test_suite.project):
                return False

            # 验证套件内至少有一个已启用的用例
            active_cases = test_suite.test_cases.filter(status='active', is_active=True).exists()
            return active_cases
        except TestSuite.DoesNotExist:
            return False

class CanViewExecutionResult(permissions.BasePermission):
    """
    执行结果查看权限
    允许项目成员查看对应项目的执行结果
    """  
    def has_object_permission(self, request, view, obj):
        # obj为TestReport或TestResult实例
        project = obj.project
        project_perm = IsProjectMember()
        return project_perm.has_object_permission(request, view, project)
    