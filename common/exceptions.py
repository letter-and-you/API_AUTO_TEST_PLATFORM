'''
Author: letterzhou
Description: -- 
Date: 2025-11-25 15:09:56
LastEditors: letterzhou
LastEditTime: 2025-11-25 15:10:05
'''
from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError, AuthenticationFailed, PermissionDenied
from rest_framework.response import Response
from rest_framework import status
import logging

logger = logging.getLogger(__name__)

class APIError(Exception):
    """自定义API异常基类"""
    def __init__(self, message, code=400, data=None):
        self.message = message
        self.code = code
        self.data = data
        super().__init__(self.message)


class ResourceNotFoundError(APIError):
    """资源不存在异常"""
    def __init__(self, message="资源不存在", data=None):
        super().__init__(message, 404, data)


class RateLimitExceededError(APIError):
    """请求频率超限异常"""
    def __init__(self, message="请求过于频繁，请稍后再试", data=None):
        super().__init__(message, 429, data)


def custom_exception_handler(exc, context):
    """自定义异常处理器"""
    # 先调用DRF默认处理器
    response = exception_handler(exc, context)
    
    # 记录异常日志
    logger.error(f"API异常: {str(exc)}, 上下文: {context}")
    
    # 处理自定义异常
    if isinstance(exc, APIError):
        return Response(
            {
                'error': exc.message,
                'code': exc.code,
                'data': exc.data or {}
            },
            status=exc.code
        )
    
    # 处理DRF内置异常
    if response is not None:
        if isinstance(exc, ValidationError):
            response.data = {
                'error': '参数验证失败',
                'code': 400,
                'details': response.data
            }
        elif isinstance(exc, AuthenticationFailed):
            response.data = {
                'error': '认证失败',
                'code': 401,
                'details': str(exc)
            }
        elif isinstance(exc, PermissionDenied):
            response.data = {
                'error': '权限不足',
                'code': 403,
                'details': str(exc)
            }
    else:
        # 未捕获的异常（500）
        response = Response(
            {
                'error': '服务器内部错误',
                'code': 500,
                'details': '请联系管理员处理' if status.HTTP_500_INTERNAL_SERVER_ERROR else str(exc)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    return response