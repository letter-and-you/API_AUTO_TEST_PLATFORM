from rest_framework import serializers
from .models import TestMachine, MachineMonitorData

class TestMachineListSerializer(serializers.ModelSerializer):
    """测试机器列表序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = TestMachine
        fields = ['id', 'name', 'ip_address', 'port', 'status', 'status_display',
                'os', 'is_active', 'created_by_name', 'created_at', 'last_heartbeat']

class TestMachineDetailSerializer(serializers.ModelSerializer):
    """测试机器详情序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = TestMachine
        fields = ['id', 'name', 'ip_address', 'port', 'description', 'status', 'status_display',
                'os', 'cpu_cores', 'memory', 'disk', 'username', 'password', 'private_key',
                'is_active', 'created_by', 'created_by_name', 'created_at', 'updated_at',
                'last_heartbeat']
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at', 'last_heartbeat', 'status']
        extra_kwargs = {
            'password': {'write_only': True},
            'private_key': {'write_only': True}
        }

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class MachineMonitorDataSerializer(serializers.ModelSerializer):
    """机器监控数据序列化器"""
    machine_name = serializers.CharField(source='machine.name', read_only=True)

    class Meta:
        model = MachineMonitorData
        fields = ['id', 'machine', 'machine_name', 'cpu_usage', 'memory_usage',
                'disk_usage', 'network_in', 'network_out', 'timestamp']
        read_only_fields = ['id', 'timestamp']