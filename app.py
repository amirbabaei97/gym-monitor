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


@app.get("/scrape")
async def scrape_endpoint():
    loop = asyncio.get_running_loop()
    # Offload the synchronous scrape function to the executor
    await loop.run_in_executor(executor, scrape)
    return {"message": "Scraping process completed."}


@app.get("/checkins/")
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
