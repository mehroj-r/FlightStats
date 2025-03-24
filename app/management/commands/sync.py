import json
from decimal import Decimal, getcontext

from django.core.management.base import BaseCommand

from app.models import Aircraft, Airport, BoardingPass, Ticket, Flight, Booking, Seat, TicketFlight
from django.db import connections

class Command(BaseCommand):
    help = "Sync data from old DB to new DB"

    def migrate_aircrafts(self):
        with connections['demo'].cursor() as cursor:
            cursor.execute("SELECT aircraft_code, model, range FROM aircrafts_data")
            for row in cursor.fetchall():
                Aircraft.objects.create(
                    aircraft_code=row[0],
                    model=json.loads(row[1]),
                    range=row[2]
                )

        self.stdout.write(self.style.SUCCESS("Aircraft data migration completed!"))

    def migrate_airports(self):

        # Set the precision for Decimal
        getcontext().prec = 17

        with connections['demo'].cursor() as cursor:
            cursor.execute("SELECT airport_code, airport_name, city, coordinates, timezone FROM airports_data")
            for row in cursor.fetchall():

                Airport.objects.create(
                    airport_code=row[0],
                    airport_name=json.loads(row[1]),
                    city=json.loads(row[2]),
                    coordinates=row[3],
                    timezone=row[4]
                )

        self.stdout.write(self.style.SUCCESS("Airport data migration completed!"))

    def migrate_bookings(self):
        with connections['demo'].cursor() as cursor:
            cursor.execute("SELECT book_ref, book_date, total_amount FROM bookings")
            for row in cursor.fetchall():
                Booking.objects.create(
                    book_ref=row[0],
                    book_date=row[1],
                    total_amount=row[2]
                )

        self.stdout.write(self.style.SUCCESS("Booking data migration completed!"))

    def migrate_tickets(self):
        with connections['demo'].cursor() as cursor:
            cursor.execute("SELECT ticket_no, book_ref, passenger_id, passenger_name, contact_data FROM tickets")
            for row in cursor.fetchall():
                Ticket.objects.create(
                    ticket_no=row[0],
                    book_ref=Booking.objects.get(book_ref=row[1]),
                    passenger_id=row[2],
                    passenger_name=row[3],
                    contact_data=json.loads(row[4]),
                )

        self.stdout.write(self.style.SUCCESS("Tickets data migration completed!"))


    def migrate_flights(self):
        with connections['demo'].cursor() as cursor:
            cursor.execute("SELECT flight_id, flight_no, scheduled_departure, scheduled_arrival, departure_airport, arrival_airport, status, aircraft_code, actual_departure, actual_arrival FROM flights")
            for row in cursor.fetchall():
                Flight.objects.create(
                    flight_id=row[0],
                    flight_no=row[1],
                    scheduled_departure=row[2],
                    scheduled_arrival=row[3],
                    departure_airport=Airport.objects.get(airport_code=row[4]),
                    arrival_airport=Airport.objects.get(airport_code=row[5]),
                    status=row[6],
                    aircraft_code=Aircraft.objects.get(aircraft_code=row[7]),
                    actual_departure=row[8],
                    actual_arrival=row[9],
                )

        self.stdout.write(self.style.SUCCESS("Flights data migration completed!"))

    def migrate_boardpasses(self):
        # Fetch all boarding passes at once

        boarding_passes = []

        print("Fetching boarding passes from demo database...")
        with connections['demo'].cursor() as cursor:
            cursor.execute("SELECT ticket_no, flight_id, boarding_no, seat_no FROM boarding_passes")
            boarding_passes = cursor.fetchall()


        if not boarding_passes:
            self.stdout.write(self.style.WARNING("No boarding passes found to migrate."))
            return

        # Get all unique ticket numbers and flight IDs to prefetch
        print("Extracting unique ticket numbers and flight IDs...")
        ticket_nos = set(row[0] for row in boarding_passes)
        flight_ids = set(row[1] for row in boarding_passes)

        # Prefetch all needed tickets and flights
        print("Prefetching tickets and flights...")
        ticket_map = {ticket.ticket_no: ticket for ticket in Ticket.objects.filter(ticket_no__in=ticket_nos)}
        flight_map = {flight.flight_id: flight for flight in Flight.objects.filter(flight_id__in=flight_ids)}


        # Create BoardingPass objects in bulk
        print("Creating BoardingPass objects...")
        boarding_pass_objects = []
        for row in boarding_passes:
            ticket_no, flight_id, boarding_no, seat_no = row

            # Skip if the ticket or flight doesn't exist in our database
            if ticket_no not in ticket_map or flight_id not in flight_map:
                self.stdout.write(self.style.WARNING(
                    f"Skipping boarding pass for ticket {ticket_no}, flight {flight_id}: related object not found"
                ))
                continue

            boarding_pass_objects.append(
                BoardingPass(
                    ticket_no=ticket_map[ticket_no],
                    flight_id=flight_map[flight_id],
                    boarding_no=boarding_no,
                    seat_no=seat_no
                )
            )

        # Use bulk_create to insert all objects in a few queries
        # Process in chunks to avoid memory issues with very large datasets
        chunk_size = 5000
        for i in range(0, len(boarding_pass_objects), chunk_size):
            BoardingPass.objects.bulk_create(boarding_pass_objects[i:i + chunk_size])
            self.stdout.write(
                self.style.SUCCESS(
                    f"Migrated boarding passes {i + 1} to {min(i + chunk_size, len(boarding_pass_objects))}")
            )

        self.stdout.write(self.style.SUCCESS(
            f"Boarding Pass data migration completed! {len(boarding_pass_objects)} records migrated."))

    def migrate_seats(self):
        with connections['demo'].cursor() as cursor:
            cursor.execute("SELECT aircraft_code, seat_no, fare_condition FROM seats")
            for row in cursor.fetchall():
                Seat.objects.create(
                    aircraft_code=Aircraft.objects.get(aircraft_code=row[0]),
                    seat_no=row[1],
                    fare_condition=row[2]
                )

        self.stdout.write(self.style.SUCCESS("Seats data migration completed!"))

    def migrate_ticketflights(self):
        batch_size = 5000
        total_migrated = 0
        skipped_count = 0

        self.stdout.write("Fetching ticket flights from demo database...")
        with connections['demo'].cursor() as cursor:
            cursor.execute("SELECT ticket_no, flight_id, fare_conditions, amount FROM tickets_flight")
            ticket_flights = cursor.fetchall()

        if not ticket_flights:
            self.stdout.write(self.style.WARNING("No ticket flights found to migrate."))
            return

        # Get all unique ticket numbers and flight IDs to prefetch
        self.stdout.write("Extracting unique ticket numbers and flight IDs...")
        ticket_nos = set(row[0] for row in ticket_flights)
        flight_ids = set(row[1] for row in ticket_flights)

        # Prefetch all needed tickets and flights
        self.stdout.write("Prefetching tickets and flights...")
        ticket_map = {ticket.ticket_no: ticket for ticket in Ticket.objects.filter(ticket_no__in=ticket_nos)}
        flight_map = {flight.flight_id: flight for flight in Flight.objects.filter(flight_id__in=flight_ids)}

        # Create TicketFlight objects in bulk
        self.stdout.write("Creating TicketFlight objects...")
        ticket_flight_objects = []
        for row in ticket_flights:
            ticket_no, flight_id, fare_conditions, amount = row

            # Skip if the ticket or flight doesn't exist in our database
            if ticket_no not in ticket_map or flight_id not in flight_map:
                self.stdout.write(self.style.WARNING(
                    f"Skipping ticket flight for ticket {ticket_no}, flight {flight_id}: related object not found"
                ))
                skipped_count += 1
                continue

            ticket_flight_objects.append(
                TicketFlight(
                    ticket_no=ticket_map[ticket_no],
                    flight_id=flight_map[flight_id],
                    fare_condition=fare_conditions,
                    amount=float(amount)
                )
            )

        # Use bulk_create to insert all objects in a few queries
        # Process in chunks to avoid memory issues with very large datasets
        for i in range(0, len(ticket_flight_objects), batch_size):
            batch = ticket_flight_objects[i:i + batch_size]
            TicketFlight.objects.bulk_create(batch)
            total_migrated += len(batch)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Migrated ticket flights {i + 1} to {min(i + batch_size, len(ticket_flight_objects))}")
            )

        self.stdout.write(self.style.SUCCESS(
            f"Ticket Flights data migration completed! {total_migrated} records migrated, {skipped_count} records skipped."))

    def migrate_airport_coordinates(self):
        from django.contrib.gis.geos import Point

        with connections['demo'].cursor() as cursor:
            cursor.execute("SELECT airport_code, coordinates FROM airports_data")
            for row in cursor.fetchall():
                try:
                    airport = Airport.objects.get(airport_code=row[0])

                    # Check if coordinates is a string that needs to be parsed as JSON
                    coordinates_data = row[1]
                    if isinstance(coordinates_data, str):
                        try:
                            # Try to parse as JSON if it's a string
                            coordinates_json = json.loads(coordinates_data)
                            # Extract lat/lon from the parsed JSON
                            lat = float(coordinates_json.get('lat', coordinates_json.get('latitude')))
                            lon = float(coordinates_json.get('lon', coordinates_json.get('lng', coordinates_json.get(
                                'longitude'))))
                        except json.JSONDecodeError:
                            # If not valid JSON, check if it's a lat,lon string
                            parts = coordinates_data.split(',')
                            if len(parts) == 2:
                                lat = float(parts[0].strip().strip('('))
                                lon = float(parts[1].strip().strip(')'))
                            else:
                                self.stdout.write(self.style.WARNING(f"Skipping {row[0]}: Invalid coordinates format"))
                                continue
                    # If it's already a dict-like object
                    elif hasattr(coordinates_data, 'get'):
                        lat = float(coordinates_data.get('lat', coordinates_data.get('latitude')))
                        lon = float(
                            coordinates_data.get('lon', coordinates_data.get('lng', coordinates_data.get('longitude'))))
                    else:
                        self.stdout.write(self.style.WARNING(f"Skipping {row[0]}: Unknown coordinates format"))
                        continue

                    # Create a Point object for GeoDjango
                    point = Point(lon, lat)  # Note: Point takes (longitude, latitude)
                    airport.coordinates = point
                    airport.save()
                    self.stdout.write(f"Updated coordinates for {row[0]}")

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error updating {row[0]}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS("Airport coordinates migration completed!"))




    def handle(self, *args, **kwargs):

        # self.migrate_aircrafts()
        # self.migrate_airports()
        # self.migrate_bookings()
        # self.migrate_tickets()
        # self.migrate_flights()
        # self.migrate_seats()
        # self.migrate_boardpasses()
        # self.migrate_ticketflights()
        self.migrate_airport_coordinates()


        self.stdout.write(self.style.SUCCESS("Data migration completed!"))