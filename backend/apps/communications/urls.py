from django.urls import path

from .views import NoticeDetailView, NoticeListCreateView, NoticePublishView

urlpatterns = [
    path('notices/', NoticeListCreateView.as_view(), name='notice-list-create'),
    path('notices/<uuid:pk>/', NoticeDetailView.as_view(), name='notice-detail'),
    path('notices/<uuid:pk>/publish/', NoticePublishView.as_view(), name='notice-publish'),
]
