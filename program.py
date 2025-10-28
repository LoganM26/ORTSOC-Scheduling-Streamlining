#!/bin/env python

from datetime import datetime
from zoneinfo import ZoneInfo
import csv
import ics

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
    # Each line must be terminated by \r\n including the final line by iCalendar spec.
    event = "".join(line + "\r\n" for line in [
        f"BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;TZID={PST}:{dtstart}",
        f"DTEND;TZID={PST}:{dtend}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{desc}",
        f"END:VEVENT"
    ])
    return event

def main():
    grcSchedulePath = "./ORTSOC GRC Fall 2025.csv"
    secopsSchedulePath = "./ORTSOC SECOPS Fall 2025.csv"
    outputPath = "./main.ics"
if __name__ == "__main__":
    main()