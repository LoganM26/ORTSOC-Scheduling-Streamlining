#!/bin/env python

from datetime import datetime, date, time, timedelta
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

# Converts a schedule index to a datetime object for a specific week start
def indexToDatetime(scheduleIndex, weekStart: date):
    dayOffsets = [0, 1, 2, 3, 4]  # Monday=0 ... Friday=4
    dayIndex = scheduleIndex // 24
    halfHourBlocks = scheduleIndex % 24
    hour = 7 + (halfHourBlocks // 2)
    minute = 30 if halfHourBlocks % 2 else 0
    dt = datetime.combine(weekStart + timedelta(days=dayOffsets[dayIndex]), time(hour, minute), PST)
    return dt

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

def generateICSEvents(schedule, weekStart: date, roleName: str):
    events = []
    students = set()
    # Create the students set
    for block in schedule:
        students.update(block)
    
    # Timestamp creation time
    dtstamp = datetime.now(PST).strftime("%Y%m%dT%H%M%S")

    # Go through all students and conjoin adjacent shifts
    for student in students:
        startIdx = None
        # Find adjacent shifts for this student
        for i, block in enumerate(schedule):
            if student in block:
                if startIdx is None:
                    startIdx = i # start a new shift
            else:
                if startIdx is not None:
                    # End of shift
                    dtstart = indexToDatetime(startIdx, weekStart).strftime("%Y%m%dT%H%M%S")
                    dtend = (indexToDatetime(i, weekStart)).strftime("%Y%m%dT%H%M%S")
                    uid = f"{student}-{roleName}-{startIdx}"
                    event = createEvent(uid, dtstamp, dtstart, dtend, f"{student} ({roleName})", f"{roleName} shift for {student}")
                    events.append(event)
                    startIdx = None
        if startIdx is not None:
            # Edge case: handle shift ending at the last block
            dtstart = indexToDatetime(startIdx, weekStart).strftime("%Y%m%dT%H%M%S")
            dtend = (indexToDatetime(len(schedule) - 1, weekStart) + timedelta(minutes=30)).strftime("%Y%m%dT%H%M%S")
            uid = f"{student}-{roleName}-{startIdx}"
            event = createEvent(uid, dtstamp, dtstart, dtend, f"{student} ({roleName})", f"{roleName} shift for {student}")
            events.append(event)

    return events



def main():
    grcSchedulePath = "./ORTSOC GRC Fall 2025.csv"
    secopsSchedulePath = "./ORTSOC SECOPS Fall 2025.csv"
    outputPath = "./main.ics"

    weekStart = date(2025, 10, 27) # example date

    # Generate schedules
    grcSchedule = parseSchedule(parseCSV(readTextFile(grcSchedulePath)))
    secopsSchedule = parseSchedule(parseCSV(readTextFile(secopsSchedulePath)))

    # Generate events
    grcEvents = generateICSEvents(grcSchedule, weekStart, "GRC")
    secopsEvents = generateICSEvents(secopsSchedule, weekStart, "SECOPS")

    # Example event
    if grcEvents:
        print("Example VEVENT:\n")
        print(grcEvents[0])
    
    with open(outputPath, "w") as f:
        f.write("BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//Generated Schedule//EN\r\n")
        for event in grcEvents + secopsEvents:
            f.write(event)
        f.write("END:VCALENDAR\r\n")

    print(f"ICS calendar written to {outputPath}")

    

if __name__ == "__main__":
    main()