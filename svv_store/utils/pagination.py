from rest_framework.pagination import PageNumberPagination

class CustomPageNumberPagination(PageNumberPagination):
    page_query_param = 'page_no'
    page_size_query_param = 'page_size'
    max_page_size = 100  # Optional: limit the max size if needed
