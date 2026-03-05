'''
Author: letterzhou
Description: 全局异常处理模块，定义基础异常类、业务异常及统一异常处理器
Date: 2025-11-25 15:09:56
LastEditors: letterzhou
LastEditTime: 2025-12-29 16:20:57
'''
from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError, AuthenticationFailed, PermissionDenied
from rest_framework.response import Response
from rest_framework import status
from django.db import DatabaseError
from django.core.exceptions import ObjectDoesNotExist
import logging

logger = logging.getLogger(__name__)


class APIError(Exception):
    """自定义API异常基类，所有业务异常需继承此类"""
    def __init__(self, message, code=400, data=None):
        self.message = message  # 错误描述信息
        self.code = code        # 错误状态码（HTTP状态码）
        self.data = data        # 附加错误数据（如字段校验详情）
        super().__init__(self.message)


class ResourceNotFoundError(APIError):
    """资源不存在异常（404）"""
    def __init__(self, message="资源不存在", data=None):
        super().__init__(message, 404, data)


class RateLimitExceededError(APIError):
    """请求频率超限异常（429）"""
    def __init__(self, message="请求过于频繁，请稍后再试", data=None):
        super().__init__(message, 429, data)


class PermissionDeniedError(APIError):
    """权限不足异常（403）"""
    def __init__(self, message="没有执行该操作的权限", data=None):
        super().__init__(message, 403, data)


class InvalidParameterError(APIError):
    """参数无效异常（400）"""
    def __init__(self, message="参数格式错误或不完整", data=None):
        super().__init__(message, 400, data)


class TaskExecutionError(APIError):
    """任务执行失败异常（500）"""
    def __init__(self, message="任务执行失败，请重试", data=None):
        super().__init__(message, 500, data)


def custom_exception_handler(exc, context):
    """
    全局异常处理器：
    1. 统一异常响应格式
    2. 处理自定义异常、DRF内置异常及Django原生异常
    3. 记录异常日志便于调试
    """
    # 调用DRF默认处理器处理内置异常（如404、405等）
    response = exception_handler(exc, context)
    
    # 记录所有异常日志（包含上下文信息）
    logger.error(
        f"API异常: {str(exc)}, "
        f"请求路径: {context.get('request').path}, "
        f"方法: {context.get('request').method}",
        exc_info=True  # 记录完整堆栈信息
    )

    # 处理自定义API异常
    if isinstance(exc, APIError):
        return Response(
            {
                'error': exc.message,
                'code': exc.code,
                'data': exc.data or {}
            },
            status=exc.code
        )

    # 处理Django数据库异常
    if isinstance(exc, DatabaseError):
        return Response(
            {
                'error': '数据库操作失败，请稍后重试',
                'code': 500,
                'data': {'detail': str(exc)} if status.HTTP_500_INTERNAL_SERVER_ERROR else {}
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # 处理Django对象不存在异常（如查询不到数据）
    if isinstance(exc, ObjectDoesNotExist):
        return Response(
            {
                'error': '指定资源不存在',
                'code': 404,
                'data': {'detail': str(exc)}
            },
            status=404
        )

    # 处理DRF内置异常（覆盖默认响应格式）
    if response is not None:
        if isinstance(exc, ValidationError):
            response.data = {
                'error': '参数验证失败',
                'code': 400,
                'data': {'details': response.data}  # 保留原始校验详情
            }
        elif isinstance(exc, AuthenticationFailed):
            response.data = {
                'error': '认证失败，请重新登录',
                'code': 401,
                'data': {'detail': str(exc)}
            }
        elif isinstance(exc, PermissionDenied):
            response.data = {
                'error': '权限不足，无法执行此操作',
                'code': 403,
                'data': {'detail': str(exc)}
            }

    # 处理未被捕获的异常（500错误）
    if response is None:
        response = Response(
            {
                'error': '服务器内部错误',
                'code': 500,
                'data': {'detail': '系统异常，请联系管理员'}
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response