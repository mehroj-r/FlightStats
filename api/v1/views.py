from pprint import pprint

from rest_framework import permissions, generics
from rest_framework.response import Response
from rest_framework.views import APIView

from app.models import Airport
from .serializers import AirportSerializer, AirportStatsPostSerializer


class AirportListAPIView(generics.ListAPIView):
    """
    API endpoint that allows airports to be viewed.
    """
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer
    permission_classes = [permissions.IsAuthenticated]



class AirportStatisticsAPIView(APIView):
    """
    API endpoint that allows airport statistics to be viewed.
    """
    permission_classes = [permissions.IsAuthenticated]

    def process_statistics(self, data):
        # TODO: Implement the logic to properly respond with the airport statistics
        pass

    def post(self, request):
        """
        Create a new airport.
        """

        pprint(request.data)

        serializer = AirportStatsPostSerializer(data=request.data)
        if serializer.is_valid():
            stats_serializer = self.process_statistics(serializer.validated_data)

            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)