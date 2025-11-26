#!/bin/env python3

from typing import Optional
import sys
from datetime import datetime, timedelta
import csv
import io
import os
import uuid

# Sets the date on which shifts start (Must be a Monday).
START_DATE = datetime(2025, 9, 15)
# Sets how many weeks the schedule should repeat for before the end of the term.
WEEKS_IN_TERM = 10
# Sets the default path of the GRC schedule in CSV format.
GRC_SCHEDULE_PATH = "./ORTSOC GRC Schedule.csv"
# Sets the default path of the SECOPS schedule in CSV format.
SECOPS_SCHEDULE_PATH = "./ORTSOC SECOPS Schedule.csv"
# Sets the default path to output ICS files into.
OUTPUT_DIRECTORY_PATH = "./"

# readTextFile: Reads the contents of a file as a UTF-8 string.
# input str filePath: A string file path. Can be a relative or rooted file path.
# return str fileContents: The full contents of the target file.
def readTextFile(filePath: str) -> str:
    filePath = os.path.realpath(os.path.expanduser(filePath))
    with open(filePath, "rb") as file:
        return file.read().decode(encoding="UTF-8")

# writeTextFile: Writes a string into a file in the UTF-8 format.
# input str filePath: A string file path. Can be a relative or rooted file path.
# input str fileContents: The full contents of the target file.
# return None
def writeTextFile(filePath: str, fileContents: str) -> None:
    filePath = os.path.realpath(os.path.expanduser(filePath))
    with open(filePath, "wb") as file:
        return file.write(fileContents.encode(encoding="UTF-8"))

# parseCSV: Parses the contents of a CSV file from a string into a 2D array of strings.
# input str rawCSV: The entire contents of the CSV file as a string.
# return list[list[str]] data: A 2D array of strings containing the data from the CSV. Can be accessed with data[x][y].
def parseCSV(rawCSV: str) -> list[list[str]]:
    stream = io.StringIO(rawCSV)
    reader = csv.reader(stream)
    rows = [row for row in reader]
    return [list(col) for col in zip(*rows)]

# removeShiftNote: Removes the note from an ORTSOC shift by locating the " (" marker.
# Notes look like this "Finlay Christ (Make up shift from 11/5)"
# If " (" is not found it simply returns the original string unchanged.
# input str text: The original input string.
# return str textTrimmed: The output after trimming.
def removeShiftNote(text: str) -> str:
    index = text.find(" (")
    if index != -1:
        return text[:index]
    else:
        return text

# timeIndexToTimeDelta: Converts a time index into a python timedelta.
# input int timeIndex: The time in time index format.
# return timedelta timeDelta: The time in timedelta format.
def timeIndexToTimeDelta(timeIndex: int) -> timedelta:
    return timedelta(minutes=(timeIndex * 30))

# timeDeltaToTimeIndex: Converts a python timedelta into a time index.
# input timedelta timeDelta: The time in timedelta format.
# return int timeIndex: The time in time index format.
def timeDeltaToTimeIndex(timeDelta: timedelta) -> int:
    if timeDelta.seconds % 1800 != 0:
        raise Exception("timeDelta was not aligned to a 30 minute block.")
    return ((timeDelta.days % 7) * 48) + (timeDelta.seconds // 1800)

# timeDeltaToHumanTime: Converts a python timedelta into a human readable string.
# The format looks like "Tuesday 07:30AM".
# input timedelta timeDelta: The time in timedelta format.
# return str humanTime: The time in human readable format.
def timeDeltaToHumanTime(timeDelta: timedelta) -> str:
    baseMonday = datetime(1970, 1, 5)
    return (baseMonday + timeDelta).strftime("%A %I:%M%p")

# humanHourToTimeDelta: Converts a human readable hour into a python timedelta.
# The format looks like "15:30".
# input str humanHour: The time in human readable 24 hour format.
# return timedelta timeDelta: The time in python timedelta format.
def humanHourToTimeDelta(humanHour: str) -> timedelta:
    dateTime = datetime.strptime(humanHour, "%H:%M")
    return timedelta(hours=dateTime.hour, minutes=dateTime.minute)

# dateTimeToICSDateTime: Converts a python datetime into ICS datetime format.
# The format looks like "America/Los_Angeles:20250105T060000Z".
# input datetime dateTime: The time in python datetime format.
# return str icsDateTime: The time in ICS date time format.
def dateTimeToICSDateTime(dateTime: datetime) -> str:
    return dateTime.strftime("%Y%m%dT%H%M%S")

# timeIndexToHumanTime: A shorthand for timeDeltaToHumanTime(timeIndexToTimeDelta(timeIndex)).
# input int timeIndex: The time in time index format.
# return str humanTime: The time in human readable format.
def timeIndexToHumanTime(timeIndex: int) -> str:
    return timeDeltaToHumanTime(timeIndexToTimeDelta(timeIndex))

# parseSchedulePhase1:
# Parses a raw ORTSOC schedule spreadsheet into a list of who was working during each time block.
# Time blocks are each 30 minutes starting at 12am on Monday and going until 11:30pm on Sunday.
# input list[list[str]] rawSpreadsheet: The raw spreadsheet in parsed CSV format unchanged from it's original form.
# return list[list[str]] schedule: A list with one element per 30 minute time block starting at 12am on Monday and going until 11:30pm on Sunday.
# Each element is another list of strings containing the names of all the people scheduled during that block.
#
# Makes the following assumptions:
# There will be times or time ranges in row 0.
# There will be a padding in column 0.
# There will be an integer in column 1 between the data for each day of the week.
# ORTSOC schedule begins on Monday.
# ORTSOC has consistent hours every day of the week.
# Each block is 30 minutes in length.
def parseSchedulePhase1(rawSpreadsheet: list[list[str]]) -> list[list[str]]:
    # Read when ORTSOC opens from cell (1, 0)
    ortsocOpenTime = timeDeltaToTimeIndex(humanHourToTimeDelta(rawSpreadsheet[1][0].split()[0]))
    # Prepare to read data by removing the first column which contains days of the week not real data.
    rawSpreadsheet = rawSpreadsheet[1:]
    # Prepare to read data by removing the first row which contains start/end times not real data.
    rawSpreadsheet = [row[1:] for row in rawSpreadsheet ]
    # Remove all shifts where the name contains "ORTSOC" as these are just markers for the ORTSOC 428 and 424 classes.
    rawSpreadsheet = [[ "" if "ORTSOC" in value else value for value in row ] for row in rawSpreadsheet]
    # Remove text in parenthesis so "Jamie (8:45)" becomes just "Jamie".
    rawSpreadsheet = [[ removeShiftNote(value) for value in row ] for row in rawSpreadsheet]

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
# field str track: Either "GRC" or "SECOPS".
# field int startTime: The time index when this shift begins.
# field int endTime: The time index when this shift ends.
class Shift:
    def __init__(self, name: str, track: str, startTime: int, endTime: int):
        self.name = name
        self.track = track
        self.startTime = startTime
        self.endTime = endTime

# parseSchedulePhase2:
# Parses a phase 1 schedule into a list of instances of the Shift class.
# input list[list[str]] phase1Schedule: A list with one element per 30 minute time block starting at 12am on Monday and going until 11:30pm on Sunday.
# Each element is another list of strings containing the names of all the people scheduled during that block.
# input str track: Either "GRC" or "SECOPS".
# return list[Shift] schedule: A list containing all of the shifts on the schedule.
def parseSchedulePhase2(phase1Schedule: list[list[str]], track: str) -> list[Shift]:
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
# input str categories: The categories of the vevent.
# input Optional[str] rrule: Optional repeat rule in string format. Set to None if undesired.
# return str icsEvent: The created vevent in proper ICS format.
def createICSEvent(title: str, description: str, startDateTime: datetime, endDateTime: datetime, categories: str, rrule: Optional[str] = None) -> str:
    # Use a random uuid as the vevent uid so it's globally unique.
    uid = str(uuid.uuid4())
    dtstamp = dateTimeToICSDateTime(datetime.now())
    dtstart = dateTimeToICSDateTime(startDateTime)
    dtend = dateTimeToICSDateTime(endDateTime)
    lines = [
        f"BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        f"DTSTART;TZID=America/Los_Angeles:{dtstart}",
        f"DTEND;TZID=America/Los_Angeles:{dtend}",
        f"SUMMARY:{title}",
        f"DESCRIPTION:{description}",
        f"CATEGORIES:{categories}",
        f"END:VEVENT"
    ]
    if rrule != None:
        lines.insert(-1, f"RRULE:{rrule}")
    # Lines must be split with "\r\n".
    return "".join([line + "\r\n" for line in lines ])

# createICSVtimezone: Builds an ICS vtimezone for PST.
# return str icsTimezone: The created vtimezone in proper ICS format.
def createICSVtimezone() -> str:
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
    # Lines must be split with "\r\n".
    return "".join([line + "\r\n" for line in lines ])

# createICSCalendar: Builds an ICS calendar by wrapping the provided components.
# Components can be vevents, vtimezones, and more.
# input list[str] components: The components of this calendar.
# return str icsCalendar: The created calendar in proper ICS format.
def createICSCalendar(components: list[str]) -> str:
    headerLines = [
        f"BEGIN:VCALENDAR",
        f"VERSION:2.0",
        f"PRODID:-//ORTSOC//ORTSOC-Scheduling-Streamlining//EN"
    ]
    header = "".join([line + "\r\n" for line in headerLines ])
    footerLines = [
        f"END:VCALENDAR"
    ]
    footer = "".join([line + "\r\n" for line in footerLines ])
    componentsPayload = "".join(components)
    return header + componentsPayload + footer

# scheduleToICSCalendar: Builds an ICS calendar out of the ORTSOC schedule.
# Optionally filters the ICS to only include shifts for a target person by their name.
# input list[Shift] schedule: An ORTSOC schedule as returned by parseSchedulePhase2.
# input Optional[str] name: The name of a person who's shifts should be in the output ICS. If name == None all shifts are included.
# return string icsCalendar: A complete ICS calendar ready to be saved to a text file.
def scheduleToICSCalendar(schedule: list[Shift], name: Optional[str] = None) -> str:
    components = []
    components.append(createICSVtimezone())
    for shift in schedule:
        if name != None and shift.name.lower() != name.lower():
            continue
        title = f"{shift.name} (ORTSOC {shift.track})"
        description = f"{shift.track} shift for {shift.name}"
        startDateTime = START_DATE + timeIndexToTimeDelta(shift.startTime)
        endDateTime = START_DATE + timeIndexToTimeDelta(shift.endTime)
        categories = shift.track
        components.append(createICSEvent(title, description, startDateTime, endDateTime, categories, "FREQ=WEEKLY;COUNT=10"))
    return createICSCalendar(components)

# Other notes:
# - Start date is manually set in code, add user input functionality (todo)
# - Events current repeat for 10 wks, technically an asummption (fix w/ user input or global var) (done)
# - Make individual schedules, prob just a flag for generateICSEvents function then call writeICalendar inside (done)
def main() -> None:
    # Gather args minus the script name.
    args = sys.argv[1:]
    # If there is only one arg and it's asking for help then print the help menu.
    if len(args) == 1:
        firstArgLower = args[0].lower()
        if firstArgLower in [ "--help", "-h", "/?"]:
            print(f"USAGE: python3 {os.path.basename(__file__)} [OPTIONS]")
            print()
            print(f"Options:")
            print(f"--help, -h         Displays this help message.")
            print(f"--grc-csv, -g      Set the file path of the GRC schedule.")
            print(f"                   Default is \"{GRC_SCHEDULE_PATH}\".")
            print(f"--secops-csv, -s   Set the file path of the SECOPS schedule.")
            print(f"                   Default is \"{SECOPS_SCHEDULE_PATH}\".")
            print(f"--output-dir, -o   Set the output folder path where ICS files will be saved.")
            print(f"                   Default is the current working directory.")
            return
    # Read the values for each arg into the variables below.
    # None means not set.
    # If invalid args are provided print and error and return from main.
    grcSchedulePath = None
    secopsSchedulePath = None
    outputDirectoryPath = None
    i = 0
    while i < len(args):
        arg = args[i]
        argLower = arg.lower()
        if argLower in [ "--grc-csv", "-g"]:
            if grcSchedulePath != None:
                print("GRC schedule path can only be set once.")
                return
            if i + 1 >= len(args):
                print(f"No value gived after arg {arg}.")
                return
            grcSchedulePath = args[i + 1]
            i += 1
        elif argLower in [ "--secops-csv", "-s" ]:
            if secopsSchedulePath != None:
                print("SECOPS schedule path can only be set once.")
                return
            if i + 1 >= len(args):
                print(f"No file path given after {arg}.")
                return
            secopsSchedulePath = args[i + 1]
            i += 1
        elif argLower in [ "--output-dir", "-o" ]:
            if outputDirectoryPath != None:
                print("Output directory path can only be set once.")
                return
            if i + 1 >= len(args):
                print(f"No file path given after {arg}.")
                return
            outputDirectoryPath = args[i + 1]
            i += 1
        elif argLower in [ "--help", "-h", "/?"]:
            print(f"Help option cannot be used with other options.")
            return
        else:
            print(f"Unknown argument {arg}. For help run python3 {os.path.basename(__file__)} --help")
            return
        i += 1
    # Set any variables to their defaults if they are currently not set.
    if grcSchedulePath == None:
        grcSchedulePath = GRC_SCHEDULE_PATH
    if secopsSchedulePath == None:
        secopsSchedulePath = SECOPS_SCHEDULE_PATH
    if outputDirectoryPath == None:
        outputDirectoryPath = OUTPUT_DIRECTORY_PATH
    # Ensure all variables are rooted full paths.
    grcSchedulePath = os.path.realpath(os.path.expanduser(grcSchedulePath))
    secopsSchedulePath = os.path.realpath(os.path.expanduser(secopsSchedulePath))
    outputDirectoryPath = os.path.realpath(os.path.expanduser(outputDirectoryPath))
    # Ensure all variables are valid paths that exist.
    if not os.path.isfile(grcSchedulePath):
        print(f"File {grcSchedulePath} does not exist.")
        return
    if not os.path.isfile(secopsSchedulePath):
        print(f"File {secopsSchedulePath} does not exist.")
        return
    if not os.path.isdir(outputDirectoryPath):
        print(f"Directory {outputDirectoryPath} does not exist.")
        return
    # Load GRC and SECOPS schedules from CSV.
    grcScheduleCSV = parseCSV(readTextFile(grcSchedulePath))
    grcSchedule = parseSchedulePhase2(parseSchedulePhase1(grcScheduleCSV), "GRC")
    secopsScheduleCSV = parseCSV(readTextFile(secopsSchedulePath))
    secopsSchedule = parseSchedulePhase2(parseSchedulePhase1(secopsScheduleCSV), "SECOPS")
    # Generate and save main ISC file.
    mainSchedule = grcSchedule + secopsSchedule
    mainIcs = scheduleToICSCalendar(mainSchedule, None)
    mainIcsPath = os.path.join(outputDirectoryPath, "main.ics")
    writeTextFile(mainIcsPath, mainIcs)
    # Generate and save individual ICS files.
    names = set([ shift.name for shift in mainSchedule ])
    individualIcsFolder = os.path.join(outputDirectoryPath, "individual")
    os.makedirs(individualIcsFolder, exist_ok=True)
    for name in names:
        individualIcs = scheduleToICSCalendar(mainSchedule, name)
        individualIcsPath = os.path.join(individualIcsFolder, name + ".ics")
        writeTextFile(individualIcsPath, individualIcs)
    # Print goodbye message and quit.
    print(f"Generated main.ics and individual ICS files for {len(names)} students and saved them into {outputDirectoryPath}.")

if __name__ == "__main__":
    print()
    try:
        main()
    except BaseException as ex:
        print(f"ERROR: {ex}.")
    print()