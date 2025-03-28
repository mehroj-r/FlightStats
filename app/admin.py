from django.contrib import admin

from app.models import Aircraft, Airport, Flight, BoardingPass, Booking, Seat, Ticket, TicketFlight

admin.site.register(Aircraft)
admin.site.register(Airport)
admin.site.register(Flight)
admin.site.register(BoardingPass)
admin.site.register(Booking)
admin.site.register(Seat)
admin.site.register(Ticket)
admin.site.register(TicketFlight)

