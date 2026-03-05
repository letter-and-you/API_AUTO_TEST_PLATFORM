from rest_framework import serializers
from .models import MockService, MockResponse
from projects.serializers import ProjectListSerializer
from apis.serializers import APIInterfaceListSerializer

class MockResponseSerializer(serializers.ModelSerializer):
    """Mock响应序列化器"""
    class Meta:
        model = MockResponse
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class MockServiceListSerializer(serializers.ModelSerializer):
    """Mock服务列表序列化器"""
    project = ProjectListSerializer(read_only=True)
    interface = APIInterfaceListSerializer(read_only=True)
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = MockService
        fields = ['id', 'name', 'project', 'interface', 'path', 'method', 
                'method_display', 'is_active', 'created_by_name', 'created_at']

class MockServiceDetailSerializer(serializers.ModelSerializer):
    """Mock服务详情序列化器"""
    project = ProjectListSerializer(read_only=True)
    interface = APIInterfaceListSerializer(read_only=True)
    responses = MockResponseSerializer(many=True, read_only=True)
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    project_id = serializers.IntegerField(write_only=True)
    interface_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = MockService
        fields = ['id', 'name', 'description', 'project', 'project_id',
                'interface', 'interface_id', 'path', 'method', 'method_display',
                'is_active', 'created_by', 'created_by_name', 'created_at', 'updated_at',
                'responses']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class MockResponseDetailSerializer(serializers.ModelSerializer):
    """Mock响应详情序列化器(用于独立操作)"""
    mock_service_name = serializers.CharField(source='mock_service.name', read_only=True)

    class Meta:
        model = MockResponse
        fields = ['id', 'mock_service', 'mock_service_name', 'name', 'priority',
                'match_type', 'match_headers', 'match_params', 'match_body',
                'status_code', 'response_headers', 'response_body', 'response_type',
                'delay', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']