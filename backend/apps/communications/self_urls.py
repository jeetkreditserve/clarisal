from django.urls import path

from .views import MyEventListView, MyNoticeListView

urlpatterns = [
    path('notices/', MyNoticeListView.as_view(), name='my-notice-list'),
    path('events/', MyEventListView.as_view(), name='my-event-list'),
]
