'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 16:49:37
LastEditors: letterzhou
LastEditTime: 2025-12-29 18:48:21
'''
from django.shortcuts import render

# Create your views here.
from celery import shared_task, current_app  
import logging
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import PerformanceTest, PerformanceMetric
from .serializers import (
    PerformanceTestListSerializer, PerformanceTestDetailSerializer,
    PerformanceMetricSerializer
)
from .permissions import IsPerformanceTestOwnerOrProjectMember
from .tasks import run_performance_test

# 初始化 logger
logger = logging.getLogger(__name__)

class PerformanceTestViewSet(viewsets.ModelViewSet):
    """性能测试任务管理接口"""
    permission_classes = [IsAuthenticated, IsPerformanceTestOwnerOrProjectMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'status', 'test_type']
    search_fields = ['name', 'description', 'project__name']
    ordering_fields = ['created_at', 'started_at', 'completed_at', 'concurrency']

    def get_serializer_class(self):
        if self.action == 'list':
            return PerformanceTestListSerializer
        return PerformanceTestDetailSerializer

    def get_queryset(self):
        """过滤用户有权访问的性能测试任务"""
        user = self.request.user
        # 自己创建的 + 所在项目的 + 公开项目的
        own_tests = PerformanceTest.objects.filter(created_by=user)
        project_tests = PerformanceTest.objects.filter(
            project__members__user=user
        )
        public_tests = PerformanceTest.objects.filter(
            project__is_public=True
        )
        return (own_tests | project_tests | public_tests).distinct().order_by('-created_at')

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """执行性能测试任务（异步）"""
        performance_test = self.get_object()
        
        if performance_test.status in ['running', 'completed']:
            return Response(
                {"error": f"测试当前状态为{performance_test.get_status_display()}，无法重复执行"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 更新状态为运行中
        performance_test.status = 'running'
        performance_test.save()
        
        # 调用Celery异步任务 + 保存 task_id 到模型（关键：取消任务需要用到）
        task = run_performance_test.delay(performance_test.id)
        performance_test.task_id = task.id  # 新增：保存任务ID到模型
        performance_test.save()
        
        return Response({
            "task_id": task.id,
            "message": "性能测试任务已启动"
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消性能测试任务（适配 Celery 5.6.0）"""
        performance_test = self.get_object()
        
        if performance_test.status != 'running':
            return Response(
                {"error": f"测试当前状态为{performance_test.get_status_display()}，无法取消"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 尝试取消Celery任务（核心修改）
        try:
            # 1. 检查 task_id 是否存在（避免空值）
            if not hasattr(performance_test, 'task_id') or not performance_test.task_id:
                logger.warning(f"性能测试 {pk} 无关联的 Celery 任务ID，跳过取消")
            else:
                # 2. Celery 5.x 正确的取消方式：通过 current_app.control.revoke
                current_app.control.revoke(
                    performance_test.task_id,
                    terminate=True,  # 强制终止任务
                    signal='SIGTERM' # 5.x 推荐显式指定终止信号
                )
                logger.info(f"成功取消 Celery 任务：{performance_test.task_id}")
        except Exception as e:
            logger.warning(f"取消性能测试任务失败: {str(e)}")
        
        # 更新状态
        performance_test.status = 'cancelled'
        performance_test.completed_at = timezone.now()
        performance_test.save()
        return Response({"message": "性能测试已取消"})

    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """获取性能测试指标数据"""
        performance_test = self.get_object()
        metrics = performance_test.metrics.all().order_by('timestamp')
        serializer = PerformanceMetricSerializer(metrics, many=True)
        return Response(serializer.data)