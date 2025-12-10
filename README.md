# ORTSOC 424 Team 4 Project
Our project is an automated tool that transforms ORTSOC’s complex Excel master schedule into clear, easy to use calendar files. By generating individual .ics schedules for every student, as well as a master .ics file for mentors, the tool eliminates the need for students to manually re-enter their rotation information into personal calendars. This directly improves efficiency and reduces the chance of scheduling errors.

# How to Use:
Use the video demonstration primarily
1. Download code from the releases page: https://github.com/LoganM26/ORTSOC-Scheduling-Streamlining/releases/tag/v1.0.1
2. Download the ORTSOC spreadsheet in .csv format
3. Place the file in the same place as the program.py file and run the python script
4. Let the code run, and then retrieve the calendar files from the file directory, or in /individual. 
Video Demonstration: https://media.oregonstate.edu/media/t/1_8zif75ks

# Script Assumptions
Some assumptions are made about the .csv input of the spreadsheet:
- There will be times or time ranges in row 0.
- There will be a padding in column 0.
- There will be an integer in column 1 between the data for each day of the week.
- ORTSOC schedule begins on Monday.
- ORTSOC has consistent hours every day of the week.
- Each block is 30 minutes in length.

# Category Work Around
Microsoft is bugged, who's surprised. <br>
After you import the .ics file, Outlook Calendar tags the events correctly but doesn't recognize the tags as their own categories. <br>
Solution: Go to Calendar Settings --> Account --> Categories and then add `GRC` and `SECOPS`
