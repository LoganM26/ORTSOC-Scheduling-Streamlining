#!/bin/env python

from datetime import datetime
from zoneinfo import ZoneInfo
import ics

PST = ZoneInfo("America/Los_Angeles")

# Reads a text file into a string
def readTextFile(filePath):
    with open(filePath, "r") as file:
        return file.read()

# Parses the raw contents of a CSV file into a 2d array of strings
def parseCSV(rawCsv: str):
    # Make all line endings unix style
    rawCsv = rawCsv.replace("\r\n", "\n")
    # Split file into an array of lines
    rows = rawCsv.split("\n")
    # Remove the last row if it is empty
    if rows[-1] == "":
        rows = rows[:-1]
    # Furthar split each row on each comma
    # Replace the rows in place for simplicity
    for i in range(len(rows)):
        rows[i] = rows[i].split(",")
    return rows

# Parses a 2d array of strings and returns a list of lists where each sublist corrisponds to a 30 minute block.
# Sublists contain the names of all the people scheduled during that 30 minute block.
# The larger containing list is split every 30 minutes 7am to 7pm Monday to Friday.
# That means to check if James is scheduled for 5:00pm on Tuesday you would run:
# print("James" in schedule[24 + 20])
# Because there are 24 times blocks in Monday 20 more pass between 7am and 5pm on Tuesday.
def parseSchedule(parsedCsv):
    for i in range(len(parsedCsv)):
        parsedCsv[i] = [name for name in parsedCsv[i] if name != ""]
    return parsedCsv

# Converts an integer index within the schedule array into a human readable time.
# Please don't ask me to document all this integer arithmetic (just trust that it works).
def scheduleTimeToHumanTime(timestamp):
    days = [ "Monday", "Tuesday", "Wednesday", "Thursday", "Friday" ]
    day = days[timestamp // 24]
    halfHourBlocks = timestamp % 24
    hour = (((halfHourBlocks // 2) + 7 - 1) % 12) + 1
    minute = "00" if (halfHourBlocks % 2) == 0 else "30"
    ampm = "am" if (halfHourBlocks // 2) + 7 < 12 else "pm"
    return f"{day} {hour}:{minute}{ampm}"

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
    grcSchedule = parseSchedule(parseCSV(readTextFile(grcSchedulePath)))
    secopsSchedule = parseSchedule(parseCSV(readTextFile(secopsSchedulePath)))

    # Print who was doing GRC and SECOPS during each 30 minute block
    for i in range(5 * 12 * 2):
        print(f"{scheduleTimeToHumanTime(i)}: GRC({", ".join(grcSchedule[i])}) SECOPS({", ".join(secopsSchedule[i])})")

if __name__ == "__main__":
    main()