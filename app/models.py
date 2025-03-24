from django.db import models
from django.contrib.gis.db import models as gis_models

class Aircraft(models.Model):
    aircraft_code = models.CharField(max_length=3, unique=True, primary_key=True)
    model = models.JSONField()
    range = models.IntegerField()

    def __str__(self):
        return self.aircraft_code

class Airport(models.Model):
    airport_code = models.CharField(max_length=3, unique=True, primary_key=True)
    airport_name = models.JSONField()
    city = models.JSONField()
    coordinates = gis_models.PointField(null=True, blank=True)
    timezone = models.TextField()

    def __str__(self):
        return f"{self.airport_name} ({self.airport_code})"

class Flight(models.Model):

    class FlightStatusChoices(models.TextChoices):
        SCHEDULED = 'Scheduled'
        DELAYED = 'Delayed'
        ARRIVED = 'Arrived'
        ONTIME = 'On Time'
        CANCELLED = 'Cancelled'

    flight_id = models.IntegerField(unique=True, primary_key=True)
    flight_no = models.CharField(max_length=6)

    scheduled_departure = models.DateTimeField()
    scheduled_arrival = models.DateTimeField()

    departure_airport = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name='departure_airport')
    arrival_airport = models.ForeignKey(Airport, on_delete=models.CASCADE, related_name='arrival_airport')

    status = models.CharField(max_length=10, choices=FlightStatusChoices, default=FlightStatusChoices.SCHEDULED)
    aircraft_code = models.ForeignKey(Aircraft, on_delete=models.CASCADE)

    actual_departure = models.DateTimeField(null=True, blank=True)
    actual_arrival = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Flight {self.flight_no} from {self.departure_airport} to {self.arrival_airport}"


class BoardingPass(models.Model):

    ticket_no = models.ForeignKey('Ticket', on_delete=models.CASCADE, db_column='ticket_no')
    flight_id = models.ForeignKey(Flight, on_delete=models.CASCADE, db_column='flight_id')
    boarding_no = models.IntegerField()
    seat_no = models.CharField(max_length=4)

    def __str__(self):
        return f"BP: {self.boarding_no}. Flight: {self.flight_id}, Seat: {self.seat_no}"

class Booking(models.Model):
    book_ref = models.CharField(max_length=6, unique=True, primary_key=True)
    book_date = models.DateTimeField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Booking: {self.book_ref}, Amount: {self.total_amount}"

class Seat(models.Model):

    class FareConditionChoices(models.TextChoices):
        ECONOMY = 'Economy'
        BUSINESS = 'Business'

    aircraft_code = models.ForeignKey(Aircraft, on_delete=models.CASCADE)
    seat_no = models.CharField(max_length=4)
    fare_condition = models.CharField(max_length=10, choices=FareConditionChoices)

    def __str__(self):
        return f"Seat {self.seat_no} ({self.fare_condition})"

class Ticket(models.Model):

    ticket_no = models.CharField(max_length=13, primary_key=True)
    book_ref = models.ForeignKey(Booking, on_delete=models.CASCADE)
    passenger_id = models.CharField(max_length=20)
    passenger_name = models.TextField()
    contact_data = models.JSONField()

    def __str__(self):
        return f"Ticket: {self.ticket_no}, Passenger: {self.passenger_name}"

class TicketFlight(models.Model):
    ticket_no = models.ForeignKey(Ticket, on_delete=models.CASCADE, db_column='ticket_no')
    flight_id = models.ForeignKey(Flight, on_delete=models.CASCADE, db_column='flight_id')
    fare_condition = models.CharField(max_length=10, choices=Seat.FareConditionChoices)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Ticket: {self.ticket_no}, Flight: {self.flight_id}, Fare Condition: {self.fare_condition}"