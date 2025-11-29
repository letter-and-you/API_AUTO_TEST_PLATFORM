'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 15:10:41
LastEditors: letterzhou
LastEditTime: 2025-11-25 15:10:49
'''
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from django.utils import timezone
from projects.models import Project

def generate_test_id():
    """生成唯一测试ID"""
    return f"test_{uuid.uuid4().hex[:12]}"


def get_request_hash(request_data):
    """计算请求数据的哈希值（用于缓存或去重）"""
    sorted_data = json.dumps(request_data, sort_keys=True).encode()
    return hashlib.md5(sorted_data).hexdigest()


def get_users_to_notify(project):
    """获取需要接收项目告警的用户列表"""
    # 项目创建者
    users = [project.created_by]
    # 项目管理员
    admin_members = project.members.filter(role='admin').values_list('user', flat=True)
    users.extend(admin_members)
    # 去重并过滤通知配置有效的用户
    return [
        user for user in set(users)
        if hasattr(user, 'notify_config') and user.notify_config.is_active
    ]


def is_within_mute_time(user):
    """判断当前时间是否在用户的静音时段内"""
    config = user.notify_config
    if not (config.mute_start and config.mute_end):
        return False
        
    now = timezone.localtime().time()
    # 处理跨天的静音时段（如22:00-08:00）
    if config.mute_start < config.mute_end:
        return config.mute_start <= now <= config.mute_end
    return now >= config.mute_start or now <= config.mute_end


def convert_seconds_to_hms(seconds):
    """将秒数转换为时分秒格式"""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h{minutes}m{seconds}s"