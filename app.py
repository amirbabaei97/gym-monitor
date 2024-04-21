from fastapi import FastAPI
import csv
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from scraper import scrape

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=1)

@app.get("/scrape")
async def scrape_endpoint():
    loop = asyncio.get_running_loop()
    # Offload the synchronous scrape function to the executor
    await loop.run_in_executor(executor, scrape)
    return {"message": "Scraping process completed."}


@app.get("/checkins/")
async def get_checkins(start_date: datetime, end_date: datetime):
    checkins = []
    with open('checkins.csv', 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            start_time = datetime.strptime(row['Start Time'], '%Y-%m-%d %H:%M:%S')
            if start_date <= start_time <= end_date:
                checkins.append(row)
    return checkins
