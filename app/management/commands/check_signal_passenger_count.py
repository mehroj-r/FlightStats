from django.core.management.base import BaseCommand
from django.db.models import Count
from django.utils import timezone

from app.models import Flight, TicketFlight, Seat, Ticket


class Command(BaseCommand):
    help = 'Populate passenger_count field for all flights based on distinct ticket count'

    def handle(self, *args, **options):

        flight = Flight.objects.get(flight_id=10692)

        previous_passenger_count = flight.passenger_count

        # Check if incrementing the passenger count works
        obj = TicketFlight.objects.create(
            fare_condition=Seat.FareConditionChoices.BUSINESS,
            amount=1000,
            flight_id=flight,
            ticket_no=Ticket.objects.get(ticket_no='0005433361930'),
        )

        flight = Flight.objects.get(flight_id=10692)

        current_passenger_count = flight.passenger_count

        if current_passenger_count == previous_passenger_count + 1:
            self.stdout.write(self.style.SUCCESS('Passenger count incremented successfully.'))
        else:
            self.stdout.write(self.style.ERROR('Passenger count increment failed.'))

        # Check if decrementing the passenger count works
        TicketFlight.objects.get(id=obj.id).delete()

        flight = Flight.objects.get(flight_id=10692)
        next_passenger_count = flight.passenger_count

        if next_passenger_count == current_passenger_count - 1:
            self.stdout.write(self.style.SUCCESS('Passenger count decremented successfully.'))
        else:
            self.stdout.write(self.style.ERROR('Passenger count decrement failed.'))

