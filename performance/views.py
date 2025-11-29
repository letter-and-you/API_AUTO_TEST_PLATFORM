'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 16:49:37
LastEditors: letterzhou
LastEditTime: 2025-11-25 20:53:29
'''
from django.shortcuts import render

# Create your views here.
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
#from .tasks import run_performance_test

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
        
        # 调用Celery异步任务
        task = run_performance_test.delay(performance_test.id)
        return Response({
            "task_id": task.id,
            "message": "性能测试任务已启动"
        })

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消性能测试任务"""
        performance_test = self.get_object()
        
        if performance_test.status != 'running':
            return Response(
                {"error": f"测试当前状态为{performance_test.get_status_display()}，无法取消"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # TODO: 实际项目中需要调用任务取消逻辑
        performance_test.status = 'cancelled'
        performance_test.save()
        return Response({"message": "性能测试已取消"})

    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        """获取性能测试指标数据"""
        performance_test = self.get_object()
        metrics = performance_test.metrics.all().order_by('timestamp')
        serializer = PerformanceMetricSerializer(metrics, many=True)
        return Response(serializer.data)