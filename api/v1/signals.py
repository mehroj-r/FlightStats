from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from app.models import TicketFlight


@receiver(post_save, sender=TicketFlight)
def update_flight_passenger_count(sender, instance, **kwargs):
    """
    Signal receiver to update the passenger count of a flight after a TicketFlight is saved.
    """
    flight = instance.flight_id
    flight.passenger_count += 1

    flight.save(update_fields=['passenger_count'])

@receiver(post_delete, sender=TicketFlight)
def decrement_flight_passenger_count(sender, instance, **kwargs):
    """
    Signal receiver to decrement the passenger count of a flight after a TicketFlight is deleted.
    """
    flight = instance.flight_id
    if flight.passenger_count > 0:
        flight.passenger_count -= 1
        flight.save(update_fields=['passenger_count'])