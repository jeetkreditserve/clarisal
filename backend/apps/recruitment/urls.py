from django.urls import path

from .views import (
    OrgApplicationListView,
    OrgApplicationStageView,
    OrgCandidateConvertView,
    OrgCandidateDetailView,
    OrgInterviewListCreateView,
    OrgJobPostingListCreateView,
    OrgOfferAcceptView,
    OrgOfferLetterView,
)

urlpatterns = [
    path('recruitment/jobs/', OrgJobPostingListCreateView.as_view(), name='recruitment-job-list-create'),
    path('recruitment/applications/', OrgApplicationListView.as_view(), name='recruitment-application-list'),
    path('recruitment/candidates/<uuid:pk>/', OrgCandidateDetailView.as_view(), name='recruitment-candidate-detail'),
    path('recruitment/candidates/<uuid:pk>/convert/', OrgCandidateConvertView.as_view(), name='recruitment-candidate-convert'),
    path('recruitment/applications/<uuid:pk>/stage/', OrgApplicationStageView.as_view(), name='recruitment-application-stage'),
    path(
        'recruitment/applications/<uuid:application_id>/interviews/',
        OrgInterviewListCreateView.as_view(),
        name='recruitment-interview-list-create',
    ),
    path(
        'recruitment/applications/<uuid:application_id>/offer/',
        OrgOfferLetterView.as_view(),
        name='recruitment-offer-create',
    ),
    path('recruitment/offers/<uuid:pk>/accept/', OrgOfferAcceptView.as_view(), name='recruitment-offer-accept'),
]
