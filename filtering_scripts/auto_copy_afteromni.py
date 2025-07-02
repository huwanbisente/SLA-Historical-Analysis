import os
import shutil
import re
from datetime import datetime

# === Configuration ===
source_folders = [
    r"SLA_VOICE HOURLY (New Pod Skills)",
    r"SLA_PBI_VOICE HOURLY Inbound Sales",
    r"SLA_Chat Hourly"
]

filtered_root = r"Filtered"
start_date = datetime.strptime("01_27_2025", "%m_%d_%Y")
end_date = datetime.strptime("07_02_2025", "%m_%d_%Y")

# Strict filename pattern:
# Start with MM_DD_YYYY, and ends with _PREV DAY or _Prev DAY
filename_pattern = re.compile(
    r"^(\d{2}_\d{2}_\d{4})_.*?_PREV DAY\.csv$", re.IGNORECASE
)

for source in source_folders:
    dest_subfolder = os.path.join(filtered_root, os.path.basename(source))
    os.makedirs(dest_subfolder, exist_ok=True)

    for filename in os.listdir(source):
        match = filename_pattern.match(filename)
        if match:
            file_date_str = match.group(1)
            try:
                file_date = datetime.strptime(file_date_str, "%m_%d_%Y")
                if start_date <= file_date <= end_date:
                    src_path = os.path.join(source, filename)
                    dst_path = os.path.join(dest_subfolder, filename)
                    shutil.copy2(src_path, dst_path)
                    print(f"Copied: {filename} → {dest_subfolder}")
            except ValueError:
                pass  # Skip invalid date formats
