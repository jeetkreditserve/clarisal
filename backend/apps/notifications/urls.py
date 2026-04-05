from django.urls import path

from .views import MyNotificationListView, MyNotificationMarkAllReadView, MyNotificationMarkReadView

urlpatterns = [
    path('notifications/', MyNotificationListView.as_view(), name='my-notification-list'),
    path('notifications/<uuid:pk>/read/', MyNotificationMarkReadView.as_view(), name='my-notification-mark-read'),
    path('notifications/mark-all-read/', MyNotificationMarkAllReadView.as_view(), name='my-notification-mark-all-read'),
]
