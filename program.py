#!/bin/env python

from datetime import datetime, date, time, timedelta
from zoneinfo import ZoneInfo
import csv
import io

PST = ZoneInfo("America/Los_Angeles")

# Reads a text file into a string
def readTextFile(filePath):
    with open(filePath, "r") as file:
        return file.read()

# Parses the raw contents of a CSV file into a 2d array of strings
def parseCSV(rawCsv):
    stream = io.StringIO(rawCsv)
    reader = csv.reader(stream)
    rows = [row for row in reader]
    return [list(col) for col in zip(*rows)]

# Parses a 2d array of strings and returns a list of lists where each sublist corrisponds to a 30 minute block.
# Sublists contain the names of all the people scheduled during that 30 minute block.
# The larger containing list is split every 30 minutes 12am to 12am Monday to Sunday.
# That means to check if James is scheduled for 5:00pm on Tuesday you would run:
# print("James" in schedule[48 + 34])
# Because there are 48 times blocks in Monday 34 more pass between 12am and 5pm on Tuesday.
#
# Makes the following assumptions about the input schedule:
# There will be a padding row at index 0
# There will be a padding column at index 0
# There will be numbers between the data for each day
# ORTSOC opens at 7:00am
# ORTSOC is open Monday through Friday and closed on weekends
# ORTSOC has consistent hours each day of the week
# Each block is 30 minutes in length
def parseSchedule(parsedCsv):
    # Remove first column which contains days of the week not real data.
    parsedCsv = parsedCsv[1:]
    # Remove first row which contains start/end times not real data.
    parsedCsv = [row[1:] for row in parsedCsv ]
    # Remove " (8:45)" from Jamie's shifts which are labled "Jamie (8:45)" for some reason.
    parsedCsv = [[ value.replace(" (8:45)", "") for value in row ] for row in parsedCsv]
    # Replace all the "ORTSOC Project (428)" values with "" so they are ignored.
    parsedCsv = [[ "" if "ORTSOC" in value else value for value in row ] for row in parsedCsv]

    output = [[] for _ in range(48 * 7)]
    ortsoc_open_time = 14 # ORTSOC schedule starts at 7:00am 
    for x in range(len(parsedCsv)):
        day = 0
        for y in range(len(parsedCsv[x])):
            if all([ c.isdigit() for c in parsedCsv[x][y] ]) and len(parsedCsv[x][y]) > 0:
                day += 1
                if day == 5:
                    break
            elif parsedCsv[x][y] != "":
                output[(day * 48) + ortsoc_open_time + x].append(parsedCsv[x][y])
    return output

# Converts an integer index within the schedule array into a human readable time.
# Please don't ask me to document all this integer arithmetic (just trust that it works).
def scheduleTimeToHumanTime(timestamp):
    days = [ "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday" ]
    timestamp = timestamp % (48 * 7)
    day = days[timestamp // 48]
    halfHourBlocks = timestamp % 48
    hour = (((halfHourBlocks // 2) - 1) % 12) + 1
    minute = "00" if (halfHourBlocks % 2) == 0 else "30"
    ampm = "am" if (halfHourBlocks // 2) < 12 else "pm"
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
    # event = "".join(line + "\r\n" for line in [
    #     f"BEGIN:VEVENT",
    #     f"UID:{uid}",
    #     f"DTSTAMP:{dtstamp}",
    #     f"DTSTART;TZID={PST}:{dtstart}",
    #     f"DTEND;TZID={PST}:{dtend}",
    #     f"SUMMARY:{summary}",
    #     f"DESCRIPTION:{desc}",
    #     f"END:VEVENT"
    # ])
    #return event
    event = [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;TZID=America/Los_Angeles:{dtstart}",
        f"DTEND;TZID=America/Los_Angeles:{dtend}",
        f"SUMMARY:{summary}",
        f"DESCRIPTION:{desc}",
        "END:VEVENT"
    ]
    return "\n".join(event) + "\n"

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

    # Print who was doing GRC and SECOPS during each 30 minute block
    for i in range(48 * 7):
        print(f"{scheduleTimeToHumanTime(i)}: GRC({", ".join(grcSchedule[i])}) SECOPS({", ".join(secopsSchedule[i])})")

if __name__ == "__main__":
    main()