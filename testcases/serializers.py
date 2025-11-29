
from rest_framework import serializers
from .models import TestCase, TestSuite
from projects.models import Project
from django.contrib.auth import get_user_model

User = get_user_model()

class TestCaseListSerializer(serializers.ModelSerializer):
    """测试用例列表序列化器（精简信息）"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    last_result = serializers.DictField(read_only=True)
    simple_body = serializers.CharField(read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TestCase
        fields = ('id', 'name', 'project_name', 'method', 'url', 'status', 
                 'simple_body', 'last_result', 'created_by_name', 'created_at')

    def get_created_by_name(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}"

class TestCaseDetailSerializer(serializers.ModelSerializer):
    """测试用例详情序列化器（完整信息）"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    last_result = serializers.DictField(read_only=True)
    created_by = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TestCase
        fields = ('id', 'name', 'description', 'project', 'project_name', 'method',
                 'url', 'headers', 'params', 'body', 'body_type', 'expected_status',
                 'expected_response', 'expected_json_schema', 'extract_rules',
                 'is_parameterized', 'parameters', 'status', 'last_result',
                 'created_by', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')

    def get_created_by(self, obj):
        return {
            'id': obj.created_by.id,
            'name': f"{obj.created_by.first_name} {obj.created_by.last_name}",
            'email': obj.created_by.email
        }

    def create(self, validated_data):
        # 设置创建人
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

    def validate_project(self, value):
        """验证项目是否可访问"""
        user = self.context['request'].user
        if value.created_by != user and not value.members.filter(user=user).exists():
            raise serializers.ValidationError("无权限访问该项目")
        return value

class TestSuiteListSerializer(serializers.ModelSerializer):
    """测试套件列表序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    case_count = serializers.IntegerField(read_only=True)
    last_execution = serializers.DictField(read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TestSuite
        fields = ('id', 'name', 'project_name', 'case_count', 'last_execution',
                 'created_by_name', 'created_at')

    def get_created_by_name(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}"

class TestSuiteDetailSerializer(serializers.ModelSerializer):
    """测试套件详情序列化器"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    case_count = serializers.IntegerField(read_only=True)
    last_execution = serializers.DictField(read_only=True)
    test_cases_detail = TestCaseListSerializer(source='test_cases', many=True, read_only=True)
    created_by = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TestSuite
        fields = ('id', 'name', 'description', 'project', 'project_name', 'test_cases',
                 'test_cases_detail', 'case_count', 'last_execution', 'created_by',
                 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')

    def get_created_by(self, obj):
        return {
            'id': obj.created_by.id,
            'name': f"{obj.created_by.first_name} {obj.created_by.last_name}",
            'email': obj.created_by.email
        }

    def create(self, validated_data):
        # 分离多对多字段
        test_cases = validated_data.pop('test_cases', [])
        validated_data['created_by'] = self.context['request'].user
        test_suite = TestSuite.objects.create(**validated_data)
        # 添加用例关联
        test_suite.test_cases.set(test_cases)
        return test_suite

    def validate(self, attrs):
        """验证用例是否属于同一项目"""
        project = attrs.get('project')
        test_cases = attrs.get('test_cases', [])
        
        for case in test_cases:
            if case.project != project:
                raise serializers.ValidationError(f"用例{case.name}不属于当前项目")
        
        # 验证项目访问权限
        user = self.context['request'].user
        if project.created_by != user and not project.members.filter(user=user).exists():
            raise serializers.ValidationError("无权限访问该项目")
        
        return attrs