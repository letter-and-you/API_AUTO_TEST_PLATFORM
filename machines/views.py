'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 16:49:08
LastEditors: letterzhou
LastEditTime: 2025-11-25 20:28:53
'''
# Create your views here.
from django.utils import timezone
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import TestMachine, MachineMonitorData
from .serializers import (
    TestMachineListSerializer, TestMachineDetailSerializer,
    MachineMonitorDataSerializer
)
from .permissions import IsMachineOwnerOrAdmin

class TestMachineViewSet(viewsets.ModelViewSet):
    """测试机器管理接口"""
    permission_classes = [IsAuthenticated, IsMachineOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'os', 'is_active']
    search_fields = ['name', 'ip_address', 'description']
    ordering_fields = ['name', 'created_at', 'last_heartbeat']

    def get_serializer_class(self):
        if self.action == 'list':
            return TestMachineListSerializer
        return TestMachineDetailSerializer

    def get_queryset(self):
        """过滤用户有权访问的测试机器"""
        user = self.request.user
        # 管理员可以看到所有机器，普通用户只能看到自己创建的
        if user.is_staff:
            return TestMachine.objects.all().order_by('name')
        return TestMachine.objects.filter(created_by=user).order_by('name')

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """切换机器启用状态"""
        machine = self.get_object()
        machine.is_active = not machine.is_active
        machine.save()
        return Response({'is_active': machine.is_active})

    @action(detail=True, methods=['post'])
    def heartbeat(self, request, pk=None):
        """接收机器心跳"""
        machine = self.get_object()
        machine.status = 'online'
        machine.last_heartbeat = timezone.now()
        machine.save()
        return Response({"status": "success"})

class MachineMonitorDataViewSet(viewsets.ModelViewSet):
    """机器监控数据接口"""
    serializer_class = MachineMonitorDataSerializer
    permission_classes = [IsAuthenticated, IsMachineOwnerOrAdmin]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['machine']
    ordering_fields = ['timestamp']
    http_method_names = ['get', 'post', 'head', 'options']  # 不允许修改历史数据

    def get_queryset(self):
        """过滤用户有权访问的监控数据"""
        user = self.request.user
        if user.is_staff:
            return MachineMonitorData.objects.all().order_by('-timestamp')
        return MachineMonitorData.objects.filter(
            machine__created_by=user
        ).order_by('-timestamp')

    def perform_create(self, serializer):
        """创建监控数据时验证机器权限"""
        machine = serializer.validated_data['machine']
        self.check_object_permissions(self.request, machine)
        serializer.save()