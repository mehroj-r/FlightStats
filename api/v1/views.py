from django.contrib.gis.db.models.functions import Distance
from django.db.models import ExpressionWrapper, DurationField, F, Subquery, OuterRef, Count, Q, FloatField, Min, Avg, \
    Value, IntegerField
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast

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
        )

        return airports

class CustomPagination(pagination.PageNumberPagination):
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
    pagination_class = CustomPagination

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

        flights = Flight.objects.filter(query)

        flights = flights.annotate(
            departure_airport_translated=KeyTextTransform(lang, F('departure_airport__airport_name')),
            arrival_airport_translated=KeyTextTransform(lang, F('arrival_airport__airport_name')),
            # Calculate flight_time at database level
            flight_time=ExpressionWrapper(
                F('scheduled_arrival') - F('scheduled_departure'),
                output_field=DurationField()
            ),
            # For passengers_count
            passengers_count=Subquery(
                TicketFlight.objects.filter(flight_id=OuterRef('pk'))
                .values('flight_id')
                .annotate(count=Count('id'))
                .values('count')
            ),
            flights_count=Subquery(
                Flight.objects.filter(
                    departure_airport=OuterRef('departure_airport'),
                    arrival_airport=OuterRef('arrival_airport')
                )
                .values('departure_airport', 'arrival_airport')
                .annotate(count=Count('flight_id'))
                .values('count')
            ),
            # For flights_count - count flights between same airports
            distance_km=Cast(
                Distance(
                    F('departure_airport__coordinates'),
                    F('arrival_airport__coordinates')
                ),
                output_field=FloatField()
            )
        )

        # If sort_field is not None, sort the queryset
        if sort_field and sort_order:
            flights = flights.order_by(sort_field)

            # If sort_order is 'desc', reverse the order
            if sort_order == 'desc':
                flights = flights.reverse()

        return flights
