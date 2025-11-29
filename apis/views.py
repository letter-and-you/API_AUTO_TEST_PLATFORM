'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 16:28:23
LastEditors: letterzhou
LastEditTime: 2025-11-25 19:12:24
'''
from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import APIInterface
from .serializers import APIInterfaceListSerializer, APIInterfaceDetailSerializer
from .permissions import IsAPIInterfaceOwnerOrProjectMember

class APIInterfaceViewSet(viewsets.ModelViewSet):
    """API接口管理接口"""
    permission_classes = [IsAuthenticated, IsAPIInterfaceOwnerOrProjectMember]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'method', 'is_active']
    search_fields = ['name', 'description', 'url', 'project__name']
    ordering_fields = ['created_at', 'updated_at', 'name']

    def get_serializer_class(self):
        if self.action == 'list':
            return APIInterfaceListSerializer
        return APIInterfaceDetailSerializer

    def get_queryset(self):
        """过滤用户有权访问的API接口"""
        user = self.request.user
        # 自己创建的 + 所在项目的 + 公开项目的
        own_interfaces = APIInterface.objects.filter(created_by=user)
        project_interfaces = APIInterface.objects.filter(
            project__members__user=user
        )
        public_interfaces = APIInterface.objects.filter(
            project__is_public=True
        )
        return (own_interfaces | project_interfaces | public_interfaces).distinct().order_by('-updated_at')

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """切换接口启用状态"""
        interface = self.get_object()
        interface.is_active = not interface.is_active
        interface.save()
        return Response({'is_active': interface.is_active})

    @action(detail=True, methods=['get'])
    def test(self, request, pk=None):
        """测试API接口连通性（简单示例）"""
        interface = self.get_object()
        # TODO: 实际项目中实现真实的API测试逻辑
        return Response({
            "status": "success",
            "message": f"接口测试成功: {interface.method} {interface.url}",
            "status_code": interface.status_code
        })