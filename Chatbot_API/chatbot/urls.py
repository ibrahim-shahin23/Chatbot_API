from django.urls import path
from .views import QueryAPIView, QueryHistoryAPIView, QueryStatusAPIView

urlpatterns = [
    path('query/', QueryAPIView.as_view(), name='query'),
    path('history/', QueryHistoryAPIView.as_view(), name='query-history'),
    path('status/<str:question_id>/', QueryStatusAPIView.as_view(), name='query-status'),
]