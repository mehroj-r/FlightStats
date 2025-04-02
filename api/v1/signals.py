from django.db import transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.gis.measure import D
from app.models import TicketFlight, AirportStats, Flight


def calculate_distance(departure_airport, arrival_airport):
    """
    Calculate the distance in kilometers between two airports using their coordinates.
    """
    if not departure_airport.coordinates or not arrival_airport.coordinates:
        return 0

    # Using Django's geographic distance calculation
    distance_in_km = D(m=departure_airport.coordinates.distance(arrival_airport.coordinates) * 100).km
    return distance_in_km


@receiver(post_save, sender=TicketFlight)
def update_flight_passenger_count(sender, instance, created, **kwargs):
    """
    Signal receiver to update the passenger count of a flight and corresponding AirportStats
    after a TicketFlight is saved.
    """
    if not created:
        return  # Exit early if TicketFlight is updated but not created

    # Increment the passenger count for the flight
    flight = instance.flight_id
    flight.passenger_count += 1
    flight.save(update_fields=['passenger_count'])

    # Update AirportStats passenger count
    stats_key = f"{flight.departure_airport_id}-{flight.arrival_airport_id}"

    with transaction.atomic():
        # Try to get existing stats first - don't calculate distance unless needed
        try:
            airport_stats = AirportStats.objects.get(flight_id=stats_key)
            airport_stats.passengers_count += 1
            airport_stats.save(update_fields=['passengers_count'])
        except AirportStats.DoesNotExist:
            # Only calculate distance when creating a new record
            distance_km = calculate_distance(flight.departure_airport, flight.arrival_airport)

            AirportStats.objects.create(
                flight_id=stats_key,
                departure_airport_name=flight.departure_airport.airport_name,
                arrival_airport_name=flight.arrival_airport.airport_name,
                departure_airport_id=flight.departure_airport_id,
                arrival_airport_id=flight.arrival_airport_id,
                distance_km=distance_km,
                flights_count=1,  # First flight for this route
                passengers_count=1,  # First passenger on this route
                flight_time=flight.scheduled_arrival - flight.scheduled_departure,
            )


@receiver(post_delete, sender=TicketFlight)
def decrement_flight_passenger_count(sender, instance, **kwargs):
    """
    Signal receiver to decrement the passenger count of a flight and corresponding AirportStats
    after a TicketFlight is deleted.
    """
    flight = instance.flight_id
    if flight.passenger_count > 0:
        flight.passenger_count -= 1
        flight.save(update_fields=['passenger_count'])

        # Update AirportStats passenger count
        stats_key = f"{flight.departure_airport_id}-{flight.arrival_airport_id}"

        airport_stats = AirportStats.objects.filter(
            flight_id=stats_key
        ).first()

        if airport_stats and airport_stats.passengers_count > 0:
            airport_stats.passengers_count -= 1
            airport_stats.save(update_fields=['passengers_count'])


@receiver(post_save, sender=Flight)
def update_airport_stats_for_flight(sender, instance, created, **kwargs):
    """
    Signal receiver to update AirportStats when a Flight is created or updated.
    Updates flight count and average flight time.
    """
    if not instance.scheduled_departure or not instance.scheduled_arrival:
        return  # Skip update if flight schedule is missing

    stats_key = f"{instance.departure_airport_id}-{instance.arrival_airport_id}"
    flight_time = instance.scheduled_arrival - instance.scheduled_departure

    try:
        # First try to get existing record
        airport_stats = AirportStats.objects.get(flight_id=stats_key)

        if created:  # This is a new flight for an existing route
            # Update flight count and passenger count
            airport_stats.flights_count += 1
            airport_stats.passengers_count += instance.passenger_count

            # Compute new average flight time
            airport_stats.flight_time = (
                    (airport_stats.flight_time * (airport_stats.flights_count - 1) + flight_time) /
                    airport_stats.flights_count
            )

            airport_stats.save(update_fields=['flights_count', 'passengers_count', 'flight_time'])
    except AirportStats.DoesNotExist:
        # Only calculate distance when creating a new AirportStats record
        distance_km = calculate_distance(instance.departure_airport, instance.arrival_airport)

        AirportStats.objects.create(
            flight_id=stats_key,
            departure_airport_name=instance.departure_airport.airport_name,
            arrival_airport_name=instance.arrival_airport.airport_name,
            departure_airport_id=instance.departure_airport_id,
            arrival_airport_id=instance.arrival_airport_id,
            distance_km=distance_km,
            flights_count=1,
            passengers_count=instance.passenger_count,
            flight_time=flight_time,
        )


@receiver(post_delete, sender=Flight)
def decrement_airport_stats_for_flight(sender, instance, **kwargs):
    """
    Signal receiver to update AirportStats when a Flight is deleted.
    Decrements flight count and updates average flight time.
    """
    stats_key = f"{instance.departure_airport_id}-{instance.arrival_airport_id}"

    airport_stats = AirportStats.objects.filter(
        flight_id=stats_key
    ).first()

    if airport_stats:
        if airport_stats.flights_count > 1:
            # Calculate flight time for this flight
            if instance.actual_departure and instance.actual_arrival:
                flight_time = instance.actual_arrival - instance.actual_departure
            else:
                flight_time = instance.scheduled_arrival - instance.scheduled_departure

            # Update flight count
            airport_stats.flights_count -= 1

            # Update average flight time
            # new_avg = (old_avg * old_count - removed_time) / new_count
            new_flight_time = (
                    (airport_stats.flight_time * (airport_stats.flights_count + 1) - flight_time) /
                    airport_stats.flights_count
            )
            airport_stats.flight_time = new_flight_time

            # Update passenger count
            airport_stats.passengers_count -= instance.passenger_count

            airport_stats.save(update_fields=['flights_count', 'flight_time', 'passengers_count'])
        else:
            # If this was the last flight for this route, consider removing the stats entry,
            # or you could set counts to zero but keep the record
            airport_stats.flights_count = 0
            airport_stats.passengers_count = 0
            airport_stats.flight_time = 0
            airport_stats.save(update_fields=['flights_count', 'passengers_count'])