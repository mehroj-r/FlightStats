import math
from datetime import timedelta
from pprint import pprint

from django.db.models import ExpressionWrapper, DurationField, F, Subquery, OuterRef, Count, Q
from django.db.models.fields import IntegerField
from django.db.models.fields.json import KeyTextTransform
from django.templatetags.i18n import language
from rest_framework import permissions, generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import Airport, Flight, TicketFlight, AirportDistance
from .serializers import AirportSerializer, AirportStatsPostSerializer, AirportStatsResponseSerializer


class AirportListAPIView(generics.ListAPIView):
    """
    API endpoint that allows airports to be viewed.
    """
    # queryset = Airport.objects.all()
    serializer_class = AirportSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        lang = self.request.headers['Accept-Language'].split(';')[0].split(',')[1]

        # Annotate the queryset with the translated airport name
        airports = Airport.objects.all().annotate(
            airport_name_translated=KeyTextTransform(lang, F('airport_name')),
            city_translated=KeyTextTransform(lang, F('city')),
        )

        return airports



class AirportStatisticsAPIView(APIView):
    """
    API endpoint that allows airport statistics to be viewed.
    """
    permission_classes = [permissions.IsAuthenticated]

    def process_statistics(self, data):

        request = self.request

        # Pagination parameters
        page = data.get('page', 1)
        page_size = data.get('page_size', 10)
        sort_field = None

        if data.get('sort_field') != "":
            sort_field = data.get('sort_field')

        sort_order = data.get('sort_order', 'asc')
        filters = data.get('filters', {})

        # Filters
        arrival_airport = filters.get('arrival_airport', None)
        departure_airport = filters.get('departure_airport', None)
        from_date = filters.get('from_date', None)
        to_date = filters.get('to_date', None)
        lang = request.headers['Accept-Language'].split(';')[0].split(',')[1]

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

        total_flights = flights.count()
        total_pages = math.ceil(total_flights / page_size)


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
            # For flights_count - count flights between same airports
            flights_count=Subquery(
                Flight.objects.filter(
                    departure_airport=OuterRef('departure_airport'),
                    arrival_airport=OuterRef('arrival_airport')
                )
                .values('departure_airport', 'arrival_airport')
                .annotate(count=Count('flight_id'))
                .values('count')
            ),
            distance_km=Subquery(
                AirportDistance.objects.filter(
                    departure_airport=OuterRef('departure_airport'),
                    arrival_airport=OuterRef('arrival_airport')
                ).values('distance_km')
            )
        )

        # If sort_field is not None, sort the queryset
        if sort_field:
            flights = flights.order_by(sort_field)

            # If sort_order is 'desc', reverse the order
            if sort_order == 'desc':
                flights = flights.reverse()

        return {
            "total_pages": total_pages,
            "current_page": page,
            "page_size": page_size,
            "flights": AirportStatsResponseSerializer(flights[page_size*(page-1): page_size* page], many=True).data
        }


    def post(self, request):

        pprint(request.data)

        serializer = AirportStatsPostSerializer(data=request.data)
        if serializer.is_valid():
            stats = self.process_statistics(serializer.validated_data)
            return Response(stats, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)