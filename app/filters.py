import django_filters

from app.models import AirportStats


class AirportStatsFilter(django_filters.FilterSet):

    from_date = django_filters.DateTimeFilter(field_name='scheduled_departure', lookup_expr='gte')
    to_date = django_filters.DateTimeFilter(field_name='scheduled_departure', lookup_expr='lte')
    arrival_airport = django_filters.CharFilter(field_name='arrival_airport_id', lookup_expr='exact')
    departure_airport = django_filters.CharFilter(field_name='departure_airport_id', lookup_expr='exact')

    class Meta:
        model = AirportStats
        fields = ['from_date', 'to_date', 'departure_airport', 'arrival_airport']