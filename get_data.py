import requests
import csv
from datetime import datetime
from dotenv import load_dotenv
import os
import json

# Load environment variables from .env file
dotenv_path = "/home/gym/.env"
load_dotenv(dotenv_path)

# Get sensitive information from environment variables
url = os.getenv("URL")
headers = json.loads(os.getenv("HEADERS"))  # Load headers from the JSON string in .env

csv_file = "/home/gym/checkins.csv"

def fetch_checkins():
    """Fetch check-in data from the API."""
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()  # Assuming JSON response is a list of dictionaries
    else:
        print(f"Failed to fetch data. Status code: {response.status_code}")
        return []

def read_existing_checkins():
    """Read existing check-ins from the CSV."""
    try:
        with open(csv_file, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            return [row for row in reader]
    except FileNotFoundError:
        return []

def write_checkins_to_csv(checkins):
    """Write check-ins to the CSV."""
    with open(csv_file, mode='w', encoding='utf-8', newline='') as file:
        fieldnames = ["Studio", "Start Time", "End Time", "Duration"]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(checkins)

def format_datetime(iso_datetime):
    """Convert ISO datetime to 'YYYY-MM-DD HH:MM:SS' format."""
    iso_datetime = iso_datetime.split('[')[0]
    fmt = "%Y-%m-%dT%H:%M:%S.%f%z"
    dt = datetime.strptime(iso_datetime, fmt)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def calculate_duration_in_minutes(start_time, end_time):
    """Calculate duration in minutes from ISO datetime strings."""
    fmt = "%Y-%m-%dT%H:%M:%S.%f%z"
    start = datetime.strptime(start_time.split('[')[0], fmt)
    end = datetime.strptime(end_time.split('[')[0], fmt)
    duration = (end - start).total_seconds()
    return int(duration // 60)  # Convert to minutes

def main():
    """Main function to handle check-in data."""
    new_checkins = fetch_checkins()
    if not new_checkins:
        print("No new data to process.")
        return

    # Read existing data
    existing_checkins = read_existing_checkins()

    # Transform existing data into a set for comparison
    existing_set = {
        (row["Studio"], row["Start Time"], row["End Time"], row["Duration"])
        for row in existing_checkins
    }

    # Prepare new data
    updated_checkins = []
    for entry in new_checkins:
        studio = entry["studioName"]
        start_time = format_datetime(entry["checkinTime"])
        end_time = format_datetime(entry["checkoutTime"])
        duration = str(calculate_duration_in_minutes(entry["checkinTime"], entry["checkoutTime"]))

        # Add if not already in the existing data
        if (studio, start_time, end_time, duration) not in existing_set:
            updated_checkins.append({
                "Studio": studio,
                "Start Time": start_time,
                "End Time": end_time,
                "Duration": duration
            })

    # Combine existing and new data
    all_checkins = existing_checkins + updated_checkins

    # Write to CSV
    write_checkins_to_csv(all_checkins)
    print(f"{len(updated_checkins)} new entries added to {csv_file}.")

if __name__ == "__main__":
    main()
