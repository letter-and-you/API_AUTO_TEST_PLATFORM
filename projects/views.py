
# Create your views here.

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Project, ProjectMember
from .serializers import (
    ProjectListSerializer, ProjectDetailSerializer, ProjectMemberSerializer
)
from .permissions import IsProjectOwnerOrAdmin, IsProjectMember

# 项目视图集
class ProjectViewSet(viewsets.ModelViewSet):
    """
    项目管理接口
    支持：创建、查询、更新、删除项目，管理项目成员
    权限：创建者拥有所有权限，成员拥有对应角色权限
    """
    permission_classes = [IsAuthenticated, IsProjectOwnerOrAdmin]

    # 根据请求动作选择不同的序列化器
    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectListSerializer
        return ProjectDetailSerializer

    # 根据用户身份过滤项目列表
    def get_queryset(self):
        user = self.request.user
        # 自己创建的项目 + 加入的项目 + 公开的项目
        created_projects = Project.objects.filter(created_by=user)
        joined_projects = Project.objects.filter(members__user=user)
        public_projects = Project.objects.filter(is_public=True)
        # 合并结果并去重
        return (created_projects | joined_projects | public_projects).distinct().order_by('-created_at')

    # 项目成员管理：添加成员
    @action(detail=True, methods=['post'], permission_classes=[IsProjectOwnerOrAdmin])
    def add_member(self, request, pk=None):
        """为项目添加成员"""
        project = self.get_object()
        serializer = ProjectMemberSerializer(
            data=request.data,
            context={'request': request, 'project': project}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # 项目成员管理：移除成员
    @action(detail=True, methods=['delete'], permission_classes=[IsProjectOwnerOrAdmin])
    def remove_member(self, request, pk=None):
        """从项目移除成员"""
        project = self.get_object()
        user_email = request.data.get('user_email')
        if not user_email:
            return Response({"error": "请提供用户邮箱"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            member = ProjectMember.objects.get(project=project, user__email=user_email)
            member.delete()
            return Response({"message": "成员已移除"}, status=status.HTTP_204_NO_CONTENT)
        except ProjectMember.DoesNotExist:
            return Response({"error": "该成员不在项目中"}, status=status.HTTP_404_NOT_FOUND)

    # 项目成员管理：更新成员角色
    @action(detail=True, methods=['patch'], permission_classes=[IsProjectOwnerOrAdmin])
    def update_member_role(self, request, pk=None):
        """更新项目成员角色"""
        project = self.get_object()
        user_email = request.data.get('user_email')
        role = request.data.get('role')
        
        if not user_email or not role:
            return Response({"error": "请提供用户邮箱和角色"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            member = ProjectMember.objects.get(project=project, user__email=user_email)
            member.role = role
            member.save()
            return Response(ProjectMemberSerializer(member).data)
        except ProjectMember.DoesNotExist:
            return Response({"error": "该成员不在项目中"}, status=status.HTTP_404_NOT_FOUND)

    # 项目统计视图
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def project_stats(self, request):
        """获取用户的项目统计信息"""
        user = request.user
        total_projects = self.get_queryset().count()
        created_projects = Project.objects.filter(created_by=user).count()
        joined_projects = Project.objects.filter(members__user=user).count()
        
        # 最近活跃的3个项目
        recent_projects = self.get_queryset()[:3]
        recent_projects_data = ProjectListSerializer(recent_projects, many=True).data
        
        return Response({
            'total_projects': total_projects,
            'created_projects': created_projects,
            'joined_projects': joined_projects,
            'recent_projects': recent_projects_data
        })