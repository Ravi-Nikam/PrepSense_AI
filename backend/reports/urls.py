from django.urls import path

from .views import LearnerReportView, MyPapersView, ObserverDashboardView

urlpatterns = [
    path("reports/dashboard/", ObserverDashboardView.as_view(), name="observer_dashboard"),
    path("reports/my-papers/", MyPapersView.as_view(), name="my_papers"),
    path("reports/learner/<int:learner_id>/", LearnerReportView.as_view(), name="learner_report"),
]
