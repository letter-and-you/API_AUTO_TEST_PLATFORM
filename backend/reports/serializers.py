'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 17:19:51
LastEditors: letterzhou
LastEditTime: 2025-11-25 20:57:00
'''
# reports/serializers.py
from rest_framework import serializers
from .models import TestReport, TestResult
from projects.serializers import ProjectMinimalSerializer
#from testcases.serializers import TestCaseListSerializer

class TestResultSerializer(serializers.ModelSerializer):
    """
    测试结果序列化器，用于详细展示单个用例的执行情况。
    """
    test_case_name = serializers.CharField(source='test_case.name', read_only=True)
    test_case_id = serializers.CharField(source='test_case.id', read_only=True)

    class Meta:
        model = TestResult
        fields = [
            'id', 'test_case_id', 'test_case_name', 'status', 'duration', 'executed_at',
            'request_headers', 'request_method', 'request_url', 'request_params', 'request_body',
            'response_status_code', 'response_headers', 'response_body',
            'error_message', 'failure_details'
        ]
        read_only_fields = fields

class TestReportListSerializer(serializers.ModelSerializer):
    """
    测试报告列表序列化器，提供概要信息。
    """
    project_name = serializers.CharField(source='project.name', read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    test_suite_name = serializers.CharField(source='test_suite.name', read_only=True, allow_null=True, allow_blank=True)

    class Meta:
        model = TestReport
        fields = [
            'id', 'name', 'project_name', 'report_type', 'status',
            'total_cases', 'passed_cases', 'failed_cases', 'success_rate',
            'created_by_username', 'created_at', 'test_suite_name'
        ]
        read_only_fields = fields

class TestReportDetailSerializer(serializers.ModelSerializer):
    """
    测试报告详情序列化器，包含所有统计信息和关联的用例结果列表。
    """
    project = ProjectMinimalSerializer(read_only=True)
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    test_results = TestResultSerializer(many=True, read_only=True)
    test_suite_name = serializers.CharField(source='test_suite.name', read_only=True, allow_null=True)
    test_case_name = serializers.CharField(source='test_case.name', read_only=True, allow_null=True)

    class Meta:
        model = TestReport
        fields = [
            'id', 'name', 'project', 'report_type', 'status',
            'test_suite_name', 'test_case_name',
            'total_cases', 'passed_cases', 'failed_cases', 'skipped_cases',
            'success_rate', 'total_duration', 'average_response_time',
            'created_by_username', 'created_at', 'completed_at',
            'test_results',
            'html_report_file' # 用于前端判断是否已生成HTML报告
        ]
        read_only_fields = fields