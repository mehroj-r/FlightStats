from rest_framework import serializers

from app.models import Airport


class AirportSerializer(serializers.ModelSerializer):
    """ Serializer for the Airport model. """

    airport_name = serializers.CharField(source='airport_name_translated')
    # city = serializers.CharField(source='city_translated')

    class Meta:
        model = Airport
        fields = ('airport_name', 'airport_code')

class AirportStatsResponseSerializer(serializers.Serializer):
    """ Serializer for response of airport stats. """
    flight_id = serializers.CharField(source='new_flight_id')
    departure_airport = serializers.CharField(source='departure_airport_translated')
    arrival_airport = serializers.CharField(source='arrival_airport_translated')
    distance_km = serializers.IntegerField()
    flights_count = serializers.IntegerField()
    passengers_count = serializers.IntegerField()
    flight_time = serializers.DurationField()
