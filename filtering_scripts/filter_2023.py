import os
import shutil
import re
from datetime import datetime

# === Configuration ===
source_to_dest = {
    r"SLA_VOICE HOURLY (New Pod Skills)": "2023 - New Pod Voice",
    r"SLA_PBI_VOICE HOURLY Inbound Sales": "2023 - PBI Voice Inbound",
    r"SLA_Chat Hourly": "2023 - Chat Hourly"
}

filtered_root = r"Filtered_2023"

# Regex pattern to match filenames starting with MM_DD_YYYY and ending in _PREV DAY.csv
filename_pattern = re.compile(
    r"^(\d{2}_\d{2}_2023)_.*?_PREV DAY\.csv$", re.IGNORECASE
)

for source, dest_name in source_to_dest.items():
    dest_subfolder = os.path.join(filtered_root, dest_name)
    os.makedirs(dest_subfolder, exist_ok=True)

    for filename in os.listdir(source):
        match = filename_pattern.match(filename)
        if match:
            file_date_str = match.group(1)
            try:
                file_date = datetime.strptime(file_date_str, "%m_%d_%Y")
                src_path = os.path.join(source, filename)
                dst_path = os.path.join(dest_subfolder, filename)
                shutil.copy2(src_path, dst_path)
                print(f"Copied: {filename} → {dest_subfolder}")
            except ValueError:
                pass  # Skip invalid dates
