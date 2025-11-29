# Create your views here.


from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import TestCase, TestSuite
from .serializers import (
    TestCaseListSerializer, TestCaseDetailSerializer,
    TestSuiteListSerializer, TestSuiteDetailSerializer
)
from .permissions import IsTestCaseOwnerOrProjectMember, IsTestSuiteOwnerOrProjectMember
from excutors.tasks import run_test_case, run_test_suite

# 测试用例视图集
class TestCaseViewSet(viewsets.ModelViewSet):
    """
    测试用例管理接口
    支持：创建、查询、更新、删除用例，执行单个用例
    权限：创建者拥有所有权限，项目成员拥有对应角色权限
    """
    permission_classes = [IsAuthenticated, IsTestCaseOwnerOrProjectMember]

    def get_serializer_class(self):
        if self.action == 'list':
            return TestCaseListSerializer
        return TestCaseDetailSerializer

    def get_queryset(self):
        """根据项目过滤用例，支持按项目ID查询"""
        user = self.request.user
        project_id = self.request.query_params.get('project_id')
        queryset = TestCase.objects.filter(is_active=True)

        # 按项目筛选
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        # 只显示用户有权访问的项目的用例
        accessible_projects = (
            user.created_projects.all() |
            user.joined_projects.all() |
            TestCase.objects.filter(project__is_public=True).values('project')
        ).distinct()
        queryset = queryset.filter(project__in=accessible_projects)

        return queryset.order_by('-created_at')

    # 执行单个测试用例（同步执行，返回即时结果）
    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """同步执行测试用例并返回结果"""
        test_case = self.get_object()
        # 调用执行任务（同步模式）
        result = run_test_case(test_case_id=test_case.id, sync=True)
        return Response(result)

    # 异步执行测试用例（返回任务ID，通过报告接口查询结果）
    @action(detail=True, methods=['post'], url_path='run-async')
    def run_async(self, request, pk=None):
        """异步执行测试用例，返回任务ID"""
        test_case = self.get_object()
        # 调用Celery任务（异步模式）
        task = run_test_case.delay(test_case_id=test_case.id, sync=False)
        return Response({"task_id": task.id, "message": "用例执行任务已提交"})

    # 软删除用例
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

# 测试套件视图集
class TestSuiteViewSet(viewsets.ModelViewSet):
    """
    测试套件管理接口
    支持：创建、查询、更新、删除套件，执行套件内所有用例
    权限：创建者拥有所有权限，项目成员拥有对应角色权限
    """
    permission_classes = [IsAuthenticated, IsTestSuiteOwnerOrProjectMember]

    def get_serializer_class(self):
        if self.action == 'list':
            return TestSuiteListSerializer
        return TestSuiteDetailSerializer

    def get_queryset(self):
        """根据项目过滤套件，支持按项目ID查询"""
        user = self.request.user
        project_id = self.request.query_params.get('project_id')
        queryset = TestSuite.objects.all()

        # 按项目筛选
        if project_id:
            queryset = queryset.filter(project_id=project_id)

        # 只显示用户有权访问的项目的套件
        accessible_projects = (
            user.created_projects.all() |
            user.joined_projects.all() |
            TestSuite.objects.filter(project__is_public=True).values('project')
        ).distinct()
        queryset = queryset.filter(project__in=accessible_projects)

        return queryset.order_by('-created_at')

    # 执行测试套件（异步）
    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """异步执行测试套件，返回任务ID"""
        test_suite = self.get_object()
        # 调用Celery任务
        task = run_test_suite.delay(
            test_suite_id=test_suite.id,
            created_by_id=request.user.id
        )
        return Response({
            "task_id": task.id,
            "message": f"测试套件执行任务已提交，包含{test_suite.case_count}个用例"
        })

    # 为套件添加用例
    @action(detail=True, methods=['post'], url_path='add-cases')
    def add_cases(self, request, pk=None):
        """为测试套件添加用例"""
        test_suite = self.get_object()
        case_ids = request.data.get('case_ids', [])
        if not case_ids:
            return Response({"error": "请提供用例ID列表"}, status=status.HTTP_400_BAD_REQUEST)

        # 验证用例是否存在且属于同一项目
        cases = TestCase.objects.filter(id__in=case_ids, project=test_suite.project, is_active=True)
        if len(cases) != len(case_ids):
            return Response({"error": "部分用例不存在或不属于当前项目"}, status=status.HTTP_400_BAD_REQUEST)

        # 添加用例（去重）
        existing_case_ids = test_suite.test_cases.values_list('id', flat=True)
        new_cases = cases.exclude(id__in=existing_case_ids)
        test_suite.test_cases.add(*new_cases)

        return Response(TestSuiteDetailSerializer(test_suite).data)

    # 从套件移除用例
    @action(detail=True, methods=['post'], url_path='remove-cases')
    def remove_cases(self, request, pk=None):
        """从测试套件移除用例"""
        test_suite = self.get_object()
        case_ids = request.data.get('case_ids', [])
        if not case_ids:
            return Response({"error": "请提供用例ID列表"}, status=status.HTTP_400_BAD_REQUEST)

        test_suite.test_cases.remove(*case_ids)
        return Response(TestSuiteDetailSerializer(test_suite).data)
