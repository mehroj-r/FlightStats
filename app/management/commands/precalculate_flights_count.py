from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from app.models import Flight

class Command(BaseCommand):
    help = 'Populate passenger_count field for all flights based on distinct ticket count'

    def handle(self, *args, **options):

        # Start the timer
        starting_time = timezone.now()

        # Count distinct tickets for each flight
        print("Counting distinct tickets for each flight...")
        flights_with_passenger_count = Flight.objects.annotate(
            ticket_count=Count('ticket', distinct=True)
        )

        # Track total flights updated
        total_updated = 0

        # Update passenger_count for each flight
        for flight in flights_with_passenger_count:
            # Only update if the count is different
            if flight.passenger_count != flight.ticket_count:
                flight.passenger_count = flight.ticket_count
                total_updated += 1
            if total_updated % 10000 == 0:
                print(f"Updated {total_updated} flights...")

        # Bulk update to save all changes
        print("Bulk updating flights...")

        for i in range(0, len(flights_with_passenger_count), 1000):
            batch = flights_with_passenger_count[i:i + 1000]
            Flight.objects.bulk_update(batch, ['passenger_count'])
            print(f"Updated batch {i // 1000 + 1}...")

        # End the timer
        ending_time = timezone.now()

        # Calculate the time taken
        time_taken = ending_time - starting_time

        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated passenger count for {total_updated} flights')
        )

        self.stdout.write(
            self.style.SUCCESS(f'Time taken: {time_taken}')
        )

