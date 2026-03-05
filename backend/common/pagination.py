from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class StandardResultsSetPagination(PageNumberPagination):
    """标准分页配置"""
    page_size = 10  # 默认每页10条
    page_size_query_param = 'page_size'  # 允许客户端通过参数指定每页数量
    max_page_size = 100  # 最大每页数量限制
    page_query_param = 'page'  # 页码参数名

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })