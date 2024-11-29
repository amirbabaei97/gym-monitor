from fastapi import FastAPI
import csv
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from fastapi.middleware.cors import CORSMiddleware
from scraper import scrape

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=1)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Specifies the origins that are allowed to make requests to your FastAPI app
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.get("/api/checkins/")
async def get_checkins(start_date: datetime = None, end_date: datetime = None):
    checkins = []
    with open('checkins.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            start_time = datetime.strptime(row['Start Time'], '%Y-%m-%d %H:%M:%S')
            # Check if start_date and end_date are provided, and filter accordingly
            if start_date and end_date:
                if start_date <= start_time <= end_date:
                    checkins.append(row)
            else:
                # If no dates are provided, append all records
                checkins.append(row)
    return checkins

#get the first entry in the csv of checkins
@app.get("/last/")
async def get_first_checkin():
    last_checkin = []
    with open('checkins.csv', 'r') as file:
        reader = csv.DictReader(file)
        last_checkin.append(next(reader))
        return last_checkin