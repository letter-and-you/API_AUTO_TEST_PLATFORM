'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 15:04:22
LastEditors: letterzhou
LastEditTime: 2025-11-25 15:04:30
'''
from rest_framework import serializers
from .models import MonitorRule, MonitorRecord, AlarmLog
#from projects.serializers import ProjectListSerializer
#from testcases.serializers import TestCaseListSerializer

class MonitorRuleSerializer(serializers.ModelSerializer):
    """监控规则序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    test_case_name = serializers.CharField(source='test_case.name', read_only=True, allow_null=True)
    created_by_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MonitorRule
        fields = [
            'id', 'project', 'project_name', 'test_case', 'test_case_name',
            'rule_type', 'threshold', 'interval', 'is_active',
            'created_by', 'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}"
        return "未知用户"

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class MonitorRecordSerializer(serializers.ModelSerializer):
    """监控记录序列化器"""
    rule_detail = MonitorRuleSerializer(source='rule', read_only=True)

    class Meta:
        model = MonitorRecord
        fields = ['id', 'rule', 'rule_detail', 'actual_value', 'status', 'message', 'executed_at']
        read_only_fields = fields  # 记录为自动生成，不允许手动修改


class AlarmLogSerializer(serializers.ModelSerializer):
    """告警日志序列化器"""
    record_detail = MonitorRecordSerializer(source='record', read_only=True)
    notified_user_names = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = AlarmLog
        fields = [
            'id', 'record', 'record_detail', 'notified_users',
            'notified_user_names', 'notify_type', 'is_success', 'message', 'created_at'
        ]
        read_only_fields = fields

    def get_notified_user_names(self, obj):
        return [f"{user.first_name} {user.last_name}" for user in obj.notified_users.all()]