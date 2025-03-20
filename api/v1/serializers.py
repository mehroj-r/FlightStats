from rest_framework import serializers

from app.models import Airport


class AirportSerializer(serializers.ModelSerializer):
    """ Serializer for the Airport model. """
    class Meta:
        model = Airport
        fields = '__all__'


class AirportStatsPostSerializer(serializers.Serializer):
    """ Serializer for post request of airport stats. """
    page = serializers.IntegerField()
    page_size = serializers.IntegerField()
    sort_field = serializers.CharField()
    sort_order = serializers.CharField()
    filters = serializers.JSONField()


class AirportStatsResponseSerializer(serializers.Serializer):
    """ Serializer for response of airport stats. """
    departure_airport = serializers.CharField()
    arrival_airport = serializers.CharField()
    distance_km = serializers.IntegerField()
    flights_count = serializers.IntegerField()
    passengers_count = serializers.IntegerField()
    flight_time = serializers.DurationField()
