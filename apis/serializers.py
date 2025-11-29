'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 19:11:40
LastEditors: letterzhou
LastEditTime: 2025-11-25 20:37:54
'''
from rest_framework import serializers
from .models import APIInterface
from projects.serializers import ProjectListSerializer

class APIInterfaceListSerializer(serializers.ModelSerializer):
    """API接口列表序列化器"""
    project = ProjectListSerializer(read_only=True)
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = APIInterface
        fields = ['id', 'name', 'project', 'method', 'method_display',
                'url', 'status_code', 'is_active', 'created_by_name', 'created_at']

class APIInterfaceDetailSerializer(serializers.ModelSerializer):
    """API接口详情序列化器"""
    project = ProjectListSerializer(read_only=True)
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    project_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = APIInterface
        fields = ['id', 'name', 'description', 'project', 'project_id',
                'method', 'method_display', 'url', 'headers', 'query_parameters',
                'request_example', 'response_example', 'status_code', 'is_active',
                'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)