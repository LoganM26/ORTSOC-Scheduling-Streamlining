#!/bin/env python
import pandas as pd
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

PST = ZoneInfo("America/Los_Angeles")

# Formats to ICS datetime
def createDatetime(date, time):
    dt = datetime.combine(date, time, PST)
    return dt.strftime("%Y%m%dT%H%M%S")

# Returns an ICS VEVENT string
"""
Parameters:
        uid (str): Unique event ID.
        dtstamp (str): DTSTAMP in ICS format (YYYYMMDDTHHMMSSZ or TZ-aware).
        dtstart (str): DTSTART in ICS format.
        dtend (str): DTEND in ICS format.
        summary (str): Event title.
        description (str): Event description.
"""
def createEvent(uid, dtstamp, dtstart, dtend, summary, desc):
    event = f"""BEGIN:VEVENT
UID:{uid}
DTSTAMP:{dtstamp}
DTSTART;TZID={PST}:{dtstart}
DTEND;TZID={PST}:{dtend}
SUMMARY:{summary}
DESCRIPTION:{desc}
END:VEVENT
"""
    
    return event


def main():
    print("Hello World!")
    inputFile = "SOC Fall Schedule.xlsx"
    outputFile = "master.ics"

if __name__ == "__main__":
    main()