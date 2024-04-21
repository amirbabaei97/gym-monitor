import csv
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import dotenv
import os

def scrape():
    # Load environment variables
    dotenv.load_dotenv()
    email = os.getenv('MYGYM_EMAIL')
    password = os.getenv('MYGYM_PASSWORD')

    # Login to the website
    login_url = 'https://www.mygym.de/api/login?redirect=/user/profil/checkins'
    login_payload = {'email': email , 'password': password}
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    # Scrapping the data
    with requests.Session() as session:
        post_response = session.post(login_url, data=login_payload, headers=headers)
        if post_response.ok:
            print("Login successful!")
            content_url = 'https://www.mygym.de/user/profil/checkins'
            page_response = session.get(content_url)
            soup = BeautifulSoup(page_response.text, 'html.parser')
            table = soup.find('table', class_='table checkins-summary')
            with open('checkins.csv', 'w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['Studio', 'Start Time', 'End Time', 'Duration'])

                for row in table.find_all('tr')[1:]:
                    cols = [ele.text.strip() for ele in row.find_all('td')]
                    studio, timespan, duration = cols
                    start_str, end_str = timespan.split(' – ')
                    start_time = datetime.strptime(start_str, '%d.%m.%Y %H:%M')
                    # Check if 'end_str' contains space, indicating it includes a date
                    if ' ' in end_str:
                        end_time = datetime.strptime(end_str, '%d.%m.%Y %H:%M')
                    else:
                        # Extract the date part from start_str and combine it with end_str
                        date_part = start_str.split(' ')[0]  # Get the date part 'dd.mm.yyyy'
                        end_time = datetime.strptime(f"{date_part} {end_str}", '%d.%m.%Y %H:%M')

                    # Adjust end_time for durations longer than 3 hours
                    if (end_time - start_time).total_seconds() > 10800:
                        end_time = start_time + timedelta(seconds=10800)
                    
                    duration_minutes = int((end_time - start_time).total_seconds() / 60)
                    writer.writerow([studio, start_time, end_time, duration_minutes])

            print("Data written to CSV.")
        else:
            print("Login failed:", post_response.status_code)

