from datetime import datetime

from django.shortcuts import render


def calendar(request):
    return render(
        request,
        "calendarapp/calendar.html",
        {
            "date": datetime.today(),
        },
    )
