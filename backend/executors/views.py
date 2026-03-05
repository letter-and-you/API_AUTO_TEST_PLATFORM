from django.shortcuts import render

# Create your views here.


from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from celery.result import AsyncResult
from django.conf import settings
from .permissions import CanExecuteTestCase, CanExecuteTestSuite, CanViewExecutionResult
from .tasks import run_test_case, run_test_suite
from reports.models import TestReport, TestResult
from reports.serializers import TestReportListSerializer, TestResultSerializer, TestReportDetailSerializer

# 执行结果视图集（统一管理报告和结果）
class ExecutionResultViewSet(viewsets.ReadOnlyModelViewSet):
    """
    执行结果查询接口
    支持：查询测试报告、查询用例执行结果、查询任务状态
    """    
    permission_classes = [IsAuthenticated, CanViewExecutionResult]
    serializer_class = TestReportListSerializer
    lookup_field = 'id'

    def get_queryset(self):
        """
        根据用户权限过滤报告
        """        
        user = self.request.user
        # 自己创建的报告 + 有权访问的项目的报告
        created_reports = TestReport.objects.filter(created_by=user)
        accessible_projects = (
            user.created_projects.all() |
            user.joined_projects.all() |
            TestReport.objects.filter(project__is_public=True).values('project')
        ).distinct()
        accessible_reports = TestReport.objects.filter(project__in=accessible_projects)
        return (created_reports | accessible_reports).distinct().order_by('-executed_at')

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TestReportDetailSerializer
        elif self.action == 'retrieve_result':
            return TestResultSerializer
        return TestReportListSerializer

    # 查询单个执行结果
    @action(detail=False, methods=['get'], url_path='result/(?P<result_id>[^/.]+)')
    def retrieve_result(self, request, result_id=None):
        """
        查询单个用例的执行结果
        """        
        try:
            result = TestResult.objects.get(id=result_id)
            self.check_object_permissions(request, result)
            serializer = self.get_serializer(result)
            return Response(serializer.data)
        except TestResult.DoesNotExist:
            return Response({"error": "执行结果不存在"}, status=status.HTTP_404_NOT_FOUND)

    # 查询任务执行状态
    @action(detail=False, methods=['get'], url_path='task-status/(?P<task_id>[^/.]+)')
    def task_status(self, request, task_id=None):
        """
        查询Celery任务的执行状态
        :param task_id: Celery任务ID
        :return: 任务状态和结果
        """        
        task = AsyncResult(task_id)
        status_map = {
            'PENDING': '等待中',
            'STARTED': '执行中',
            'SUCCESS': '执行成功',
            'FAILURE': '执行失败',
            'RETRY': '重试中',
            'REVOKED': '已取消'
        }
        response_data = {
            "task_id": task_id,
            "status": status_map.get(task.status, task.status),
            "result": task.result if task.status == 'SUCCESS' else None,
            "error": str(task.result) if task.status == 'FAILURE' else None
        }
        return Response(response_data)

    # 取消任务执行
    @action(detail=False, methods=['post'], url_path='cancel-task/(?P<task_id>[^/.]+)')
    def cancel_task(self, request, task_id=None):
        """
        取消正在执行的Celery任务
        仅允许任务创建者或管理员取消
        """        
        task = AsyncResult(task_id)
        # 检查任务是否可取消
        if task.status in ['PENDING', 'STARTED', 'RETRY']:
            # 取消任务
            task.revoke(terminate=True)
            return Response({"message": "任务已取消"})
        else:
            return Response(
                {"error": f"任务当前状态为{task.status}，无法取消"},
                status=status.HTTP_400_BAD_REQUEST
            )

    # 查询项目的执行历史
    @action(detail=False, methods=['get'], url_path='project/(?P<project_id>[^/.]+)')
    def project_history(self, request, project_id=None):
        """
        查询指定项目的执行历史
        """        
        # 验证项目权限
        from projects.models import Project
        try:
            project = Project.objects.get(id=project_id)
            self.check_object_permissions(request, project)
        except Project.DoesNotExist:
            return Response({"error": "项目不存在"}, status=status.HTTP_404_NOT_FOUND)

        # 筛选该项目的报告
        reports = TestReport.objects.filter(project_id=project_id).order_by('-executed_at')
        # 分页处理
        page = self.paginate_queryset(reports)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(reports, many=True)
        return Response(serializer.data)