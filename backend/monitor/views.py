'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 00:11:26
LastEditors: letterzhou
LastEditTime: 2025-12-04 19:57:26
'''
# Create your views here.

from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from projects.models import Project
from .models import MonitorRule, MonitorRecord, AlarmLog
from .serializers import MonitorRuleSerializer, MonitorRecordSerializer, AlarmLogSerializer
from .permissions import IsMonitorRuleOwner, CanViewAlarmLogs

class MonitorRuleViewSet(viewsets.ModelViewSet):
    """监控规则管理接口"""
    serializer_class = MonitorRuleSerializer
    permission_classes = [IsAuthenticated, IsMonitorRuleOwner]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'test_case', 'rule_type', 'is_active']
    search_fields = ['project__name', 'test_case__name']
    ordering_fields = ['created_at', 'interval', 'threshold']

    def get_queryset(self):
        user = self.request.user
        # 可见范围：自己创建的规则 + 所在项目的规则 + 公开项目的规则
        own_rules = MonitorRule.objects.filter(created_by=user)
        project_rules = MonitorRule.objects.filter(
            project__members__user=user
        )
        public_rules = MonitorRule.objects.filter(
            project__is_public=True
        )
        return (own_rules | project_rules | public_rules).distinct()

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """切换规则启用状态"""
        rule = self.get_object()
        rule.is_active = not rule.is_active
        rule.save()
        return Response({'is_active': rule.is_active})


class MonitorRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """监控记录查询接口"""
    serializer_class = MonitorRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['rule', 'status', 'rule__project']
    ordering_fields = ['executed_at', 'actual_value']

    def get_queryset(self):
        user = self.request.user
        # 过滤可见项目的记录
        visible_projects = [
            p.id for p in user.created_projects.all()
        ] + [
            m.project.id for m in user.joined_projects.all()
        ] + [
            p.id for p in Project.objects.filter(is_public=True)
        ]
        return MonitorRecord.objects.filter(rule__project_id__in=visible_projects)


class AlarmLogViewSet(viewsets.ReadOnlyModelViewSet):
    """告警日志查询接口"""
    serializer_class = AlarmLogSerializer
    permission_classes = [IsAuthenticated, CanViewAlarmLogs]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['notify_type', 'is_success', 'record__rule__project']
    ordering_fields = ['created_at']

    def get_queryset(self):
        user = self.request.user
        visible_projects = [
            p.id for p in user.created_projects.all()
        ] + [
            m.project.id for m in user.joined_projects.all()
        ] + [
            p.id for p in Project.objects.filter(is_public=True)
        ]
        return AlarmLog.objects.filter(
            record__rule__project_id__in=visible_projects
        ).select_related('record__rule__project').prefetch_related('notified_users')