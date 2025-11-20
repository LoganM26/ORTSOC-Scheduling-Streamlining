#!/bin/env python3

from datetime import datetime, timedelta
import csv
import io
import os
import uuid

# Sets the date on which shifts start (Must be a Monday).
START_DATE = datetime(2025, 9, 15)
# Sets how many weeks the schedule should repeat for before ending for the term.
WEEKS_IN_TERM = 10
# Sets the path of the GRC schedule in CSV format.
GRC_SCHEDULE_PATH = "./ORTSOC GRC Fall 2025.csv"
# Sets the path of the SECOPS schedule in CSV format.
SECOPS_SCHEDULE_PATH = "./ORTSOC SECOPS Fall 2025.csv"
# Sets the path of the main ICS file.
MAIN_ICS_PATH = "./main.ics"
# Sets the path of the folder containing the individual ICS files.
INDIVIDUAL_ICS_FOLDER = "./individual"

# readTextFile: Reads the contents of a file as a UTF-8 string.
# input str filePath: A string file path. Can be a relative or rooted file path.
# return str fileContents: The full contents of the target file.
def readTextFile(filePath):
    filePath = os.path.realpath(os.path.expanduser(filePath))
    with open(filePath, "rb") as file:
        return file.read().decode(encoding="UTF-8")

# writeTextFile: Writes a string into a file in the UTF-8 format.
# input str filePath: A string file path. Can be a relative or rooted file path.
# input str fileContents: The full contents of the target file.
# return None
def writeTextFile(filePath, fileContents):
    filePath = os.path.realpath(os.path.expanduser(filePath))
    with open(filePath, "wb") as file:
        return file.write(fileContents.encode(encoding="UTF-8"))

# parseCSV: Parses the contents of a CSV file from a string into a 2D array of strings.
# input str rawCSV: The entire contents of the CSV file as a string.
# return list[list[str]] data: A 2D array of strings containing the data from the CSV. Can be accessed with data[x][y].
def parseCSV(rawCSV):
    stream = io.StringIO(rawCSV)
    reader = csv.reader(stream)
    rows = [row for row in reader]
    return [list(col) for col in zip(*rows)]

# removeNoteShiftNote: Removes the note from an ORTSOC shift by locating the " (" marker.
# Notes look like this "Finlay Christ (Make up shift from 11/5)"
# If " (" is not found it simply returns the original string unchanged.
# input str text: The original input string.
# return str textTrimmed: The output after trimming.
def removeNoteShiftNote(text):
    index = text.find(" (")
    if index != -1:
        return text[:index]
    else:
        return text

# timeIndexToTimeDelta: Converts a time index into a python timedelta.
# input int timeIndex: The time in time index format.
# return timedelta timeDelta: The time in timedelta format.
def timeIndexToTimeDelta(timeIndex):
    return timedelta(minutes=(timeIndex * 30))

# timeDeltaToTimeIndex: Converts a python timedelta into a time index.
# input timedelta timeDelta: The time in timedelta format.
# return int timeIndex: The time in time index format.
def timeDeltaToTimeIndex(timeDelta):
    if timeDelta.seconds % 1800 != 0:
        raise Exception("timeDelta was not aligned to a 30 minute block.")
    return ((timeDelta.days % 7) * 48) + (timeDelta.seconds // 1800)

# timeDeltaToHumanTime: Converts a python timedelta into a human readable string.
# The format looks like "Tuesday 07:30AM".
# input timedelta timeDelta: The time in timedelta format.
# return str humanTime: The time in human readable format.
def timeDeltaToHumanTime(timeDelta):
    baseMonday = datetime(1970, 1, 5)
    return (baseMonday + timeDelta).strftime("%A %I:%M%p")

# humanHourToTimeDelta: Converts a human readable hour into a python timedelta.
# The format looks like "15:30".
# input str humanHour: The time in human readable 24 hour format.
# return timedelta timeDelta: The time in python timedelta format.
def humanHourToTimeDelta(humanHour):
    dateTime = datetime.strptime(humanHour, "%H:%M")
    return timedelta(hours=dateTime.hour, minutes=dateTime.minute)

# dateTimeToICSDateTime: Converts a python datetime into ICS datetime format.
# The format looks like "America/Los_Angeles:20250105T060000Z".
# input datetime dateTime: The time in python datetime format.
# return str icsDateTime: The time in ICS date time format.
def dateTimeToICSDateTime(dateTime):
    return "TZID=America/Los_Angeles:" + dateTime.strftime("%Y%m%dT%H%M%S")

# timeIndexToHumanTime: A shorthand for timeDeltaToHumanTime(timeIndexToTimeDelta(timeIndex)).
# input int timeIndex: The time in time index format.
# input timedelta timeDelta: The time in timedelta format.
# return str humanTime: The time in human readable format.
def timeIndexToHumanTime(timeIndex):
    return timeDeltaToHumanTime(timeIndexToTimeDelta(timeIndex))

# parseSchedulePhase1:
# Parses a raw ORTSOC schedule spreadsheet into a list of who was working during each time block.
# Time blocks are each 30 minutes starting at 12am on Monday and going until 11:30pm on Sunday.
#
# input list[list[str]] rawSpreadsheet:
# The raw spreadsheet in parsed CSV format unchanged from it's original form.
#
# return list[list[str]] schedule:
# A list with one element per 30 minute time block starting at 12am on Monday and going until 11:30pm on Sunday.
# Each element is another list of strings containing the names of all the people scheduled during that block.
#
# Makes the following assumptions:
# There will be times or time ranges in row 0
# There will be a padding in column 0
# There will be an integer in column 1 between the data for each day of the week.
# ORTSOC schedule begins on Monday
# ORTSOC has consistent hours every day of the week.
# Each block is 30 minutes in length
def parseSchedulePhase1(rawSpreadsheet):
    # Read when ORTSOC opens from cell (1, 0)
    ortsocOpenTime = timeDeltaToTimeIndex(humanHourToTimeDelta(rawSpreadsheet[1][0].split()[0]))
    # Prepare to read data by removing the first column which contains days of the week not real data.
    rawSpreadsheet = rawSpreadsheet[1:]
    # Prepare to read data by removing the first row which contains start/end times not real data.
    rawSpreadsheet = [row[1:] for row in rawSpreadsheet ]
    # Remove all shifts where the name contains "ORTSOC" as these are just markers for the ORTSOC 428 and 424 classes.
    rawSpreadsheet = [[ "" if "ORTSOC" in value else value for value in row ] for row in rawSpreadsheet]
    # Remove text in parenthesis so "Jamie (8:45)" becomes just "Jamie".
    rawSpreadsheet = [[ removeNoteShiftNote(value) for value in row ] for row in rawSpreadsheet]

    # Output should have 2 * 24 * 7 = 336 time blocks to account for all the 30 minute time blocks in a week. 
    output = [[] for _ in range(336)]
    day = 0
    for y in range(len(rawSpreadsheet[0])):
        if all([ c.isdigit() for c in rawSpreadsheet[0][y] ]) and len(rawSpreadsheet[0][y]) > 0:
            day += 1
            if day >= 5:
                break
            else:
                continue
        for x in range(len(rawSpreadsheet)):
            if rawSpreadsheet[x][y] != "":
                output[(day * 48) + ortsocOpenTime + x].append(rawSpreadsheet[x][y])
    return output

# Shift: A class for storing data about a shift at ORTSOC
# field str name: The name of the person who's shift this is.
# field int startTime: The time index when this shift begins.
# field int endTime: The time index when this shift ends.
# field str track: Either "GRC" or "SECOPS".
class Shift:
    def __init__(self, name, track, startTime, endTime):
        self.name = name
        self.track = track
        self.startTime = startTime
        self.endTime = endTime

# parseSchedulePhase2:
# Parses a phase 1 schedule into a list of instances of the Shift class.
#
# input list[list[str]] phase1Schedule:
# A list with one element per 30 minute time block starting at 12am on Monday and going until 11:30pm on Sunday.
# Each element is another list of strings containing the names of all the people scheduled during that block.
#
# return list[Shift] schedule:
# A list containing all of the shifts on the schedule.
def parseSchedulePhase2(phase1Schedule, track):
    output = []
    shiftsLastBlock = {}
    shiftsThisBlock = {}
    for i in range(len(phase1Schedule)):
        for name in phase1Schedule[i]:
            if name in shiftsLastBlock:
                shiftsLastBlock[name].endTime = i + 1
                shiftsThisBlock[name] = shiftsLastBlock[name]
                del shiftsLastBlock[name]
            else:
                shiftsThisBlock[name] = Shift(name, track, i, i + 1)
        output.extend(shiftsLastBlock.values())
        shiftsLastBlock = shiftsThisBlock
        shiftsThisBlock = {}
    return output

# createICSEvent: Builds an ICS vevent from the given input.
# input str title: The title of the vevent.
# input str description: The description of the vevent.
# input datetime startDateTime: The starting date and time of the vevent.
# input datetime endDateTime: The ending date and time of the vevent.
# input str rrule: Optional repeat rule in string format. Set to None if undesired.
# return str icsEvent: The created vevent in proper ICS format.
def createICSEvent(title, description, startDateTime, endDateTime, rrule=None):
    # Use a random uuid as the vevent uid so it's globally unique.
    uid = str(uuid.uuid4())
    dtstamp = dateTimeToICSDateTime(datetime.now())
    dtstart = dateTimeToICSDateTime(startDateTime)
    dtend = dateTimeToICSDateTime(endDateTime)
    lines = [
        f"BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;{dtstart}",
        f"DTEND;{dtend}{"\nRRULE:" + rrule if rrule != None else ""}",
        f"SUMMARY:{title}",
        f"DESCRIPTION:{description}",
        f"END:VEVENT"
    ]
    # Lines must be split with "\n".
    return "".join([line + "\n" for line in lines ])

# createICSVtimezone: Builds an ICS vtimezone for PST.
# return str icsTimezone: The created vtimezone in proper ICS format.
def createICSVtimezone():
    lines = [
        f"BEGIN:VTIMEZONE",
        f"TZID:America/Los_Angeles",
        f"BEGIN:STANDARD",
        f"DTSTART:20231105T020000",
        f"TZOFFSETFROM:-0700",
        f"TZOFFSETTO:-0800",
        f"TZNAME:PST",
        f"END:STANDARD",
        f"BEGIN:DAYLIGHT",
        f"DTSTART:20240310T020000",
        f"TZOFFSETFROM:-0800",
        f"TZOFFSETTO:-0700",
        f"TZNAME:PDT",
        f"END:DAYLIGHT",
        f"END:VTIMEZONE"
    ]
    # Lines must be split with "\n".
    return "".join([line + "\n" for line in lines ])

# createICSCalendar: Builds an ICS calendar by wrapping the provided components.
# Components can be vevents, vtimezones, and more.
# input list[str] components: The components of this calendar.
# return str icsCalendar: The created calendar in proper ICS format.
def createICSCalendar(components):
    headerLines = [
        f"BEGIN:VCALENDAR",
        f"VERSION:2.0",
        f"PRODID:-//ORTSOC//ORTSOC-Scheduling-Streamlining//EN"
    ]
    header = "".join([line + "\n" for line in headerLines ])
    footerLines = [
        f"END:VCALENDAR"
    ]
    footer = "".join([line + "\n" for line in footerLines ])
    componentsPayload = "".join(components)
    return header + componentsPayload + footer

# scheduleToICSCalendar: Builds an ICS calendar out of the ORTSOC schedule.
# Optionally filters the ICS to only include shifts for a target person by their name.
# input list[Shift] schedule: An ORTSOC schedule as returned by parseSchedulePhase2.
# input optional[str] person: The name of a person who's shifts should be in the output ICS. If person == None all shifts are included.
# return string icsCalendar: A complete ICS calendar ready to be saved to a text file.
def scheduleToICSCalendar(schedule, person: str):
    components = []
    components.append(createICSVtimezone())
    for shift in schedule:
        if person != None and shift.name.lower() != person.lower():
            continue
        title = f"{shift.name} (ORTSOC {shift.track})"
        description = f"{shift.name} working {shift.track} at ORTSOC from {timeIndexToHumanTime(shift.startTime)} to {timeIndexToHumanTime(shift.endTime)}."
        startDateTime = START_DATE + timeIndexToTimeDelta(shift.startTime)
        endDateTime = START_DATE + timeIndexToTimeDelta(shift.endTime)
        components.append(createICSEvent(title, description, startDateTime, endDateTime, "FREQ=WEEKLY;COUNT=10"))
    return createICSCalendar(components)

# Other notes:
# - Start date is manually set in code, add user input functionality (todo)
# - Events current repeat for 10 wks, technically an asummption (fix w/ user input or global var) (done)
# - Make individual schedules, prob just a flag for generateICSEvents function then call writeICalendar inside (done)
def main():
    grcScheduleCSV = parseCSV(readTextFile(GRC_SCHEDULE_PATH))
    grcSchedule = parseSchedulePhase2(parseSchedulePhase1(grcScheduleCSV), "GRC")
    secopsScheduleCSV = parseCSV(readTextFile(SECOPS_SCHEDULE_PATH))
    secopsSchedule = parseSchedulePhase2(parseSchedulePhase1(secopsScheduleCSV), "SECOPS")
    schedule = grcSchedule + secopsSchedule

    mainIcs = scheduleToICSCalendar(schedule, None)
    writeTextFile(MAIN_ICS_PATH, mainIcs)
    print(f"Main ICS calendar written to {MAIN_ICS_PATH}.")
    
    os.makedirs(INDIVIDUAL_ICS_FOLDER, exist_ok=True)
    print("Enter a name to generate an individual ICS calendar. Leave blank to generate for all students.")
    person = input()
    if person != "":
        if not any([ person == shift.name for shift in schedule ]):
            print(f"No shifts found for {person}. No individual calendar generated.")
        else:
            individualIcsPath = os.path.join(INDIVIDUAL_ICS_FOLDER, person + ".ics")
            individualIcs = scheduleToICSCalendar(schedule, person)
            writeTextFile(individualIcsPath, individualIcs)
            print(f"ICS personal calendar for {person} written to {individualIcsPath}")
    else:
        names = set([ shift.name for shift in schedule ])
        for name in names:
            individualIcsPath = os.path.join(INDIVIDUAL_ICS_FOLDER, name + ".ics")
            individualIcs = scheduleToICSCalendar(schedule, name)
            writeTextFile(individualIcsPath, individualIcs)
        print(f"Individual ICS calendars for all {len(names)} students written into {INDIVIDUAL_ICS_FOLDER}.")

if __name__ == "__main__":
    main()