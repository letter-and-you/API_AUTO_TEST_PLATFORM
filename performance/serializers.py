from rest_framework import serializers
from .models import PerformanceTest, PerformanceMetric
from projects.serializers import ProjectListSerializer
from testcases.serializers import TestCaseListSerializer, TestSuiteListSerializer
from machines.serializers import TestMachineListSerializer

class PerformanceMetricSerializer(serializers.ModelSerializer):
    """性能指标序列化器"""
    class Meta:
        model = PerformanceMetric
        fields = '__all__'
        read_only_fields = ['id', 'timestamp']

class PerformanceTestListSerializer(serializers.ModelSerializer):
    """性能测试列表序列化器"""
    project = ProjectListSerializer(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = PerformanceTest
        fields = ['id', 'name', 'project', 'status', 'status_display', 
                'concurrency', 'duration', 'created_by_name', 'created_at']

class PerformanceTestDetailSerializer(serializers.ModelSerializer):
    """性能测试详情序列化器"""
    project = ProjectListSerializer(read_only=True)
    test_case = TestCaseListSerializer(read_only=True)
    test_suite = TestSuiteListSerializer(read_only=True)
    machine = TestMachineListSerializer(read_only=True)
    metrics = PerformanceMetricSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    project_id = serializers.IntegerField(write_only=True)
    test_case_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    test_suite_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    machine_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = PerformanceTest
        fields = ['id', 'name', 'description', 'project', 'project_id',
                        'test_type', 'test_case', 'test_case_id', 'test_suite', 'test_suite_id',
                        'concurrency', 'duration', 'ramp_up', 'loop_count', 'timeout',
                        'machine', 'machine_id', 'status', 'status_display',
                        'created_by', 'created_by_name', 'created_at', 'started_at', 'completed_at',
                        'metrics']
        read_only_fields = ['id', 'status', 'created_by', 'created_at', 'started_at', 'completed_at']

    def validate(self, data):
        """验证测试类型与关联对象的一致性"""
        test_type = data.get('test_type')
        test_case_id = data.get('test_case_id')
        test_suite_id = data.get('test_suite_id')

        if test_type == 'case' and not test_case_id:
            raise serializers.ValidationError("测试类型为单测试用例时，必须指定test_case_id")
        if test_type == 'suite' and not test_suite_id:
            raise serializers.ValidationError("测试类型为测试套件时，必须指定test_suite_id")
        
        return data

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)