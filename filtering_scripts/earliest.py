import os
import re
from datetime import datetime

# Folder containing your CSV files
folder_path = r"SLA_Chat Hourly"

# Regex pattern: Match MM_DD_YYYY at start and _PREV DAY.csv at end
filename_pattern = re.compile(r"^(\d{2})_(\d{2})_(\d{4}).*?_PREV DAY\.csv$", re.IGNORECASE)

# List to store valid dates
dates = []

# Loop through files in the folder
for filename in os.listdir(folder_path):
    match = filename_pattern.match(filename)
    if match:
        month, day, year = match.groups()
        try:
            file_date = datetime.strptime(f"{month}_{day}_{year}", "%m_%d_%Y")
            dates.append(file_date)
        except ValueError:
            continue  # Skip invalid dates

# Output the earliest valid date
if dates:
    earliest_date = min(dates)
    print("Earliest date:", earliest_date.strftime("%m/%d/%Y"))
else:
    print("No valid '_PREV DAY' files with valid dates found.")
