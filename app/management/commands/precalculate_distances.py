
import math

from django.core.management.base import BaseCommand

from app.models import Airport, AirportDistance


class Command(BaseCommand):
    help = "Sync data from old DB to new DB"

    def haversine(self, lat1, lon1, lat2, lon2):
        R = 6371  # Earth radius in km

        # Convert degrees to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])

        # Differences
        dlat = lat2 - lat1
        dlon = lon2 - lon1

        # Haversine formula
        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c  # Distance in km

    def handle(self, *args, **options):

        print("Prefetching all airports...")
        airports = Airport.objects.all()
        n = len(airports)
        distances = []

        print("Calculating distances...")
        for i in range(n):
            for j in range(n):

                if i == j:
                    continue

                airport1 = airports[i]
                airport2 = airports[j]


                lat1 = airport1.latitude
                lon1 = airport1.longitude

                lat2 = airport2.latitude
                lon2 = airport2.longitude

                distance = self.haversine(lat1, lon1, lat2, lon2)

                # Save the distance to the database
                distances.append(
                    AirportDistance(
                        departure_airport=airport1,
                        arrival_airport=airport2,
                        distance_km=distance
                    )
                )

        # Bulk create distances to optimize database operations
        print("Bulk creating distances...")
        AirportDistance.objects.bulk_create(distances)

        self.stdout.write(self.style.SUCCESS("Distance calculations are completed!"))