from pprint import pprint

from django.contrib.gis.db.models.functions import Distance
from django.core.paginator import Paginator
from django.db import connection, models
from django.db.models import ExpressionWrapper, DurationField, F, Subquery, OuterRef, Count, Q, FloatField, Min, Avg, \
    Value, IntegerField, Prefetch
from django.db.models.fields.json import KeyTextTransform
from django.db.models.functions import Cast, Concat

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


class CustomPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 10

    def paginate_queryset(self, queryset, request, view=None):
        """
        Override to use a more efficient pagination method.

        This method attempts to minimize the number of database queries
        by using Django's Paginator with a calculated count.
        """
        page_size = self.get_page_size(request)

        # Use a more efficient counting method
        try:
            # For queryset with annotations, use len() which is more efficient
            total_count = len(queryset)
        except TypeError:
            # Fallback to .count() if len() doesn't work
            total_count = queryset.count()

        # Create a paginator with the pre-calculated count
        paginator = Paginator(queryset, page_size)

        # Get the page number from the request
        page_number = request.query_params.get(self.page_query_param, 1)

        try:
            page_number = int(page_number)
        except ValueError:
            page_number = 1

        # Ensure page number is within valid range
        page_number = max(1, min(page_number, paginator.num_pages))

        # Get the page
        page = paginator.page(page_number)

        # Store pagination attributes for later use in get_paginated_response
        self.page = page
        self.request = request

        return list(page)

    def get_paginated_response(self, data):
        """
        Custom response with page metadata.
        """
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

        flights = Flight.objects.filter(query).values(
            'departure_airport', 'arrival_airport'
        ).annotate(

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

            # Total passengers using subquery
            passengers_count= Count('ticket', distinct=True),

            # Total flights using subquery
            flights_count=Count('flight_id', distinct= True),

            # Distance between airports
            distance_km=Cast(
                Distance(
                    F('departure_airport__coordinates'),
                    F('arrival_airport__coordinates')
                ),
                output_field=FloatField()
            ) / 1_000,
        )

        # If sort_field is not None, sort the queryset
        if sort_field:
            if sort_order == 'desc':
                sort_field = f'-{sort_field}'
            flights = flights.order_by(sort_field)

        return flights