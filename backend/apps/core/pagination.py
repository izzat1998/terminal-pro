"""
Centralized pagination classes for consistent API responses.
"""

from collections import OrderedDict

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination for list endpoints.

    - Default page size: 20 items
    - Clients can customize page size with ?page_size=X
    - Max page size: 100 items

    Response format:
    {
        "success": true,
        "count": 100,
        "next": "http://api.example.com/entries/?page=3",
        "previous": "http://api.example.com/entries/?page=1",
        "results": [...]
    }
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            OrderedDict(
                [
                    ("success", True),
                    ("count", self.page.paginator.count),
                    ("next", self.get_next_link()),
                    ("previous", self.get_previous_link()),
                    ("results", data),
                ]
            )
        )
