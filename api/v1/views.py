
from django.db import models
from django.db.models import F
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Concat
from django.utils.translation import get_language
from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import permissions, generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from app.filters import AirportStatsFilter
from app.models import Airport, Flight, AirportStats
from .serializers import AirportSerializer, AirportStatsResponseSerializer


class AirportListAPIView(generics.ListAPIView):
    """
    API endpoint that allows airports to be viewed.
    """
    serializer_class = AirportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        lang = get_language()

        if '-' in lang:
            lang = lang.split('-')[0]

        # Annotate the queryset with the translated airport name
        airports = Airport.objects.all().annotate(
            airport_name_translated=KeyTextTransform(lang, F('airport_name')),
            city_translated=KeyTextTransform(lang, F('city')),
        ).order_by('airport_name')

        return airports

class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 10

    def get_paginated_response(self, data):
        return Response({
            'page': self.page.number,
            'page_count': self.page.paginator.num_pages,
            'results': data
        })

class AirportStatisticsAPIView(generics.ListAPIView):
    """
    API endpoint that allows airport statistics to be viewed.
    """
    serializer_class = AirportStatsResponseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AirportStatsFilter
    pagination_class = CustomPagination

    def get_queryset(self):

        request = self.request
        data = request.query_params

        sort_field = None
        sort_order = None

        if data.get('sort_field') != "":
            sort_field = data.get('sort_field')
            sort_order = data.get('sort_order', 'asc')

        # Language extraction from request headers (default to 'en' if not found)
        lang = get_language()

        if '-' in lang:
            lang = lang.split('-')[0]

        airport_stats = AirportStats.objects.all().annotate(

            # Airport translated name
            departure_airport_translated=Cast(
                KeyTextTransform(lang, F('departure_airport_name')), output_field=models.TextField()
            ),
            arrival_airport_translated=Cast(
                KeyTextTransform(lang, F('arrival_airport_name')), output_field=models.TextField()
            ),
        )

        # If sort_field is not None, sort the queryset
        if sort_field:
            if sort_order == 'desc':
                sort_field = f'-{sort_field}'
            airport_stats = airport_stats.order_by(sort_field)

        return airport_stats