from pprint import pprint

from django.contrib.gis.db.models.functions import Distance
from django.core.paginator import Paginator
from django.db import connection, models
from django.db.models import ExpressionWrapper, DurationField, F, Subquery, OuterRef, Count, Q, FloatField, Min, Avg, \
    Value, IntegerField, Prefetch
from django.db.models.expressions import RawSQL
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Concat, Coalesce

from rest_framework import permissions, generics, status, pagination
from rest_framework.response import Response

from app.models import Airport, Flight, TicketFlight
from .serializers import AirportSerializer, AirportStatsResponseSerializer


class AirportListAPIView(generics.ListAPIView):
    """
    API endpoint that allows airports to be viewed.
    """
    serializer_class = AirportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Language extraction from request headers (default to 'en' if not found)
        lang_header = self.request.headers.get('Accept-Language', '')
        lang_parts = lang_header.split(';')[0].split(',')
        lang = lang_parts[1] if len(lang_parts) > 1 else lang_parts[0] if lang_parts else 'en'

        # Annotate the queryset with the translated airport name
        airports = Airport.objects.all().annotate(
            airport_name_translated=KeyTextTransform(lang, F('airport_name')),
            city_translated=KeyTextTransform(lang, F('city')),
        ).order_by('airport_name')

        return airports

class AirportStatisticsAPIView(generics.ListAPIView):
    """
    API endpoint that allows airport statistics to be viewed.
    """
    serializer_class = AirportStatsResponseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):

        page_count = Flight.objects.count() / int(request.query_params.get('page_size', 10))

        return Response({
            'page': int(request.query_params.get('page',1)),
            'page_count': int(page_count),
            'results': self.list(request, *args, **kwargs),
        })

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return serializer.data

    def get_queryset(self):

        request = self.request
        data = request.query_params

        sort_field = None
        sort_order = None

        if data.get('sort_field') != "":
            sort_field = data.get('sort_field')
            sort_order = data.get('sort_order', 'asc')

        # Filters
        arrival_airport = data.get('arrival_airport', None)
        departure_airport = data.get('departure_airport', None)
        from_date = data.get('from_date', None)
        to_date = data.get('to_date', None)

        # Pagination
        page = int(data.get('page', 1))
        page_size = int(data.get('page_size', 10))

        # Language extraction from request headers (default to 'en' if not found)
        lang_header = request.headers.get('Accept-Language', '')
        lang_parts = lang_header.split(';')[0].split(',')
        lang = lang_parts[1] if len(lang_parts) > 1 else lang_parts[0] if lang_parts else 'en'

        # Initialize a Q object
        query = Q()

        # Dynamically add filters if they exist
        if arrival_airport:
            query &= Q(arrival_airport__airport_code=arrival_airport)
        if departure_airport:
            query &= Q(departure_airport__airport_code=departure_airport)
        if from_date:
            query &= Q(scheduled_departure__gte=from_date)
        if to_date:
            query &= Q(scheduled_departure__lte=to_date)

        flights = (Flight.objects.filter(query)
            .select_related('departure_airport', 'arrival_airport')
            .prefetch_related('ticketflight__ticket_no')
            .values('departure_airport', 'arrival_airport')
            .annotate(

            # Create a unique flight_id by concatenating airport codes
            new_flight_id=Concat(
                F('departure_airport__airport_code'),
                Value('-'),
                F('arrival_airport__airport_code')
            ),

            # Airport translated name
            departure_airport_translated=Cast(
                KeyTextTransform(lang, F('departure_airport__airport_name')), output_field=models.TextField()
            ),
            arrival_airport_translated=Cast(
                KeyTextTransform(lang, F('arrival_airport__airport_name')), output_field=models.TextField()
            ),

            # Average flight time
            flight_time=Avg(
                ExpressionWrapper(
                    F('scheduled_arrival') - F('scheduled_departure'),
                    output_field=DurationField()
                )
            ),

            # Total passengers
            passengers_count=Count('ticketflight__ticket_no', distinct=True),
            # passengers_count= Count('ticket', distinct=True),

            # passengers_count=Cast(
            #     1, output_field=IntegerField()
            # ),
            # Total flights
            flights_count=Count('flight_id', distinct= True),

            # Distance between airports
            distance_km=Cast(
                Distance(
                    F('departure_airport__coordinates'),
                    F('arrival_airport__coordinates')
                ),
                output_field=FloatField()
            ) / 1_000,
        ))

        # If sort_field is not None, sort the queryset
        if sort_field:
            if sort_order == 'desc':
                sort_field = f'-{sort_field}'
            flights = flights.order_by(sort_field)

        return flights[(page - 1) * page_size: page * page_size]