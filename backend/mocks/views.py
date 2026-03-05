'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 16:35:43
LastEditors: letterzhou
LastEditTime: 2025-12-26 14:04:52
'''
from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import MockService, MockResponse
from .serializers import (
    MockServiceListSerializer, MockServiceDetailSerializer,
    MockResponseSerializer, MockResponseDetailSerializer
)
from .permissions import IsMockServiceOwnerOrProjectMember

class MockServiceViewSet(viewsets.ModelViewSet):
    """Mock服务管理接口"""
    permission_classes = [IsAuthenticated, IsMockServiceOwnerOrProjectMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'interface', 'method', 'is_active']
    search_fields = ['name', 'description', 'path', 'project__name']
    ordering_fields = ['created_at', 'updated_at', 'name']

    def get_serializer_class(self):
        if self.action == 'list':
            return MockServiceListSerializer
        return MockServiceDetailSerializer

    def get_queryset(self):
        """过滤用户有权访问的Mock服务"""
        user = self.request.user
        # 自己创建的 + 所在项目的 + 公开项目的
        own_services = MockService.objects.filter(created_by=user)
        project_services = MockService.objects.filter(
            project__members__user=user
        )
        public_services = MockService.objects.filter(
            project__is_public=True
        )
        return (own_services | project_services | public_services).distinct().order_by('-updated_at')

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """切换Mock服务启用状态"""
        mock_service = self.get_object()
        mock_service.is_active = not mock_service.is_active
        mock_service.save()
        return Response({'is_active': mock_service.is_active})
    
    @action(detail=True, methods=['post'])
    def get_response(self, request, pk=None):
        """根据请求匹配最合适的Mock响应（按优先级）"""
        mock_service = self.get_object()
        # 获取请求信息
        request_headers = dict(request.headers)
        request_params = request.query_params.dict()
        request_body = request.body.decode() if request.body else ''
        
        # 按优先级降序检查所有响应
        for response in mock_service.responses.order_by('-priority'):
            if response.matches_request(request_headers, request_params, request_body):
                # 模拟响应延迟
                import time
                if response.delay > 0:
                    time.sleep(response.delay / 1000)  # 转换为秒
                return Response(
                    response.response_body,
                    status=response.status_code,
                    headers=response.response_headers
                )
        
        # 无匹配响应时返回404
        return Response({"error": "No matching response found"}, status=404)

class MockResponseViewSet(viewsets.ModelViewSet):
    """Mock响应配置管理接口"""
    serializer_class = MockResponseDetailSerializer
    permission_classes = [IsAuthenticated, IsMockServiceOwnerOrProjectMember]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['mock_service']
    ordering_fields = ['priority', 'created_at']

    def get_queryset(self):
        """过滤用户有权访问的Mock响应"""
        user = self.request.user
        # 关联到有权访问的Mock服务的响应
        from django.db.models import Q
        return MockResponse.objects.filter(
            Q(mock_service__created_by=user) |
            Q(mock_service__project__members__user=user) |
            Q(mock_service__project__is_public=True)
        ).distinct().order_by('-priority')

    def perform_create(self, serializer):
        """创建响应时验证所属服务权限"""
        mock_service = serializer.validated_data['mock_service']
        self.check_object_permissions(self.request, mock_service)
        serializer.save()