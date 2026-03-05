#序列化器
from rest_framework import serializers
from .models import Project, ProjectMember
from django.contrib.auth import get_user_model

User = get_user_model()

# 项目列表序列化器（精简信息）
class ProjectListSerializer(serializers.ModelSerializer):
    """用于项目列表展示的序列化器，包含核心统计信息"""
    case_count = serializers.IntegerField(read_only=True)
    last_test_time = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S')
    success_rate = serializers.FloatField(read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'name', 'description', 'case_count', 'last_test_time', 'success_rate', 'created_by_name', 'created_at')

    def get_created_by_name(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}"

# 项目详情序列化器（完整信息）
class ProjectDetailSerializer(serializers.ModelSerializer):
    """用于项目详情展示和编辑的序列化器"""
    case_count = serializers.IntegerField(read_only=True)
    last_test_time = serializers.DateTimeField(read_only=True, format='%Y-%m-%d %H:%M:%S')
    success_rate = serializers.FloatField(read_only=True)
    created_by = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ('id', 'name', 'description', 'is_public', 'case_count', 'last_test_time', 'success_rate', 'created_by', 'members', 'created_at', 'updated_at')
        read_only_fields = ('created_by', 'created_at', 'updated_at')

    def get_created_by(self, obj):
        return {
            'id': obj.created_by.id,
            'name': f"{obj.created_by.first_name} {obj.created_by.last_name}",
            'email': obj.created_by.email
        }

    def get_members(self, obj):
        """获取项目成员列表"""
        members = obj.members.select_related('user').all()
        return [
            {
                'id': member.user.id,
                'name': f"{member.user.first_name} {member.user.last_name}",
                'email': member.user.email,
                'role': member.role,
                'joined_at': member.joined_at.strftime('%Y-%m-%d %H:%M:%S')
            } for member in members
        ]

    # 创建项目时设置创建人
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

# 项目成员序列化器
class ProjectMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(write_only=True)
    user_name = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = ProjectMember
        fields = ('id', 'user_email', 'user_name', 'role', 'joined_at')
        read_only_fields = ('id', 'joined_at', 'user_name')

    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}"

    # 验证用户是否存在
    def validate_user_email(self, value):
        try:
            User.objects.get(email=value)
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("该用户不存在")

    # 验证用户是否已在项目中
    def validate(self, attrs):
        project = self.context['project']
        user_email = attrs['user_email']
        user = User.objects.get(email=user_email)
        
        # 不能添加自己为成员（创建者默认拥有所有权限）
        if user == project.created_by:
            raise serializers.ValidationError({"user_email": "不能添加项目创建者为成员"})
        
        # 不能重复添加成员
        if ProjectMember.objects.filter(project=project, user=user).exists():
            raise serializers.ValidationError({"user_email": "该用户已在项目中"})
        
        return attrs

    # 创建成员关联
    def create(self, validated_data):
        user_email = validated_data.pop('user_email')
        user = User.objects.get(email=user_email)
        project = self.context['project']
        return ProjectMember.objects.create(project=project, user=user,** validated_data)

class ProjectMinimalSerializer(serializers.ModelSerializer):
    """极简项目序列化器（用于报表/执行器模块的轻量展示）"""
    class Meta:
        model = Project
        fields = ['id', 'name', 'code', 'created_at']  # 只返回核心字段，符合「minimal」设计

# 保留原有序列化器（如 ProjectDetailSerializer）
class ProjectDetailSerializer(serializers.ModelSerializer):
    """项目详情序列化器（原有逻辑不变）"""
    class Meta:
        model = Project
        fields = '__all__'