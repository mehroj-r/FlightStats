from django.urls import path, include

from api.v1.views import AirportListAPIView, AirportStatisticsAPIView

urlpatterns = [
    path('airports/', AirportListAPIView.as_view(), name='airport-list'),
    path('airport-statistics/', AirportStatisticsAPIView.as_view(), name='airport-stats'),
]