'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 15:10:22
LastEditors: letterzhou
LastEditTime: 2025-11-25 15:10:31
'''
import time
import logging
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

logger = logging.getLogger('request_log')

class RequestLogMiddleware(MiddlewareMixin):
    """请求日志中间件"""
    def process_request(self, request):
        # 记录请求开始时间
        request.start_time = time.time()
        # 记录请求基本信息
        if request.method != 'OPTIONS':  # 忽略OPTIONS请求
            logger.info(
                f"请求开始: {request.method} {request.path} "
                f"IP: {self.get_client_ip(request)} "
                f"用户: {request.user if request.user.is_authenticated else '匿名'}"
            )

    def process_response(self, request, response):
        # 计算请求耗时
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
            # 记录响应信息
            if request.method != 'OPTIONS':
                logger.info(
                    f"请求结束: {request.method} {request.path} "
                    f"状态码: {response.status_code} "
                    f"耗时: {duration:.2f}s"
                )
        return response

    @staticmethod
    def get_client_ip(request):
        """获取客户端真实IP"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


class RateLimitMiddleware(MiddlewareMixin):
    """请求频率限制中间件"""
    def __init__(self, get_response):
        self.get_response = get_response
        self.request_counts = {}  # {ip: [timestamp1, timestamp2...]}

    def __call__(self, request):
        # 跳过白名单IP
        if self.is_whitelisted(request):
            return self.get_response(request)
            
        # 限制逻辑（1分钟内最多60次请求）
        ip = self.get_client_ip(request)
        now = time.time()
        self.cleanup_old_records(ip, now)
        
        if len(self.request_counts.get(ip, [])) >= 60:
            from .exceptions import RateLimitExceededError
            raise RateLimitExceededError()
            
        # 记录请求时间
        self.request_counts.setdefault(ip, []).append(now)
        return self.get_response(request)

    def cleanup_old_records(self, ip, now):
        """清理1分钟前的记录"""
        if ip in self.request_counts:
            self.request_counts[ip] = [t for t in self.request_counts[ip] if now - t < 60]

    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

    @staticmethod
    def is_whitelisted(request):
        """检查IP是否在白名单"""
        ip = RateLimitMiddleware.get_client_ip(request)
        return ip in settings.IP_WHITELIST if hasattr(settings, 'IP_WHITELIST') else False