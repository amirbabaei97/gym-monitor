
# Project Title: Gym Wall of Shame

Welcome to the **Gym Wall of Shame** project, where we combine the magic of FastAPI and the charm of Svelte to create a web application that's not just functional but also judgemental. Our project features a FastAPI backend that scrapes my gym's attendance data because let's face it, everyone needs to know when I hit the weights!

![Screenshot of the wall of shame](https://i.ibb.co/3WqrxJY/Screenshot-2024-05-10-at-18-05-09.png)

## FastAPI Python Application

Nestled in the root directory, you'll find FastAPI:
- **app.py**: The beating heart of our operation, directing traffic like a pro.
- **scraper.py**: This little spy is tailored to work exclusively with my gym. It’s on a mission to fetch all my check-ins, so I can’t pretend I was at the gym when I was actually munching on pizza.

### Getting Started
Unleash the power of our FastAPI application by following these steps: (Remember, you need to modify the scrapper for your own gym!)

1. Create a virtual environment:
   ```bash
   python3 -m venv env
   source env/bin/activate
   ```
2. Install the packages from `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

#### Running the Operations
- To launch the main app:
  ```bash
  uvicorn app:app --reload
  ```

## Svelte Web Application

This shiny knight resides in the `website` directory, ready to publicly shame me!

### Getting Started
Follow these steps:

1. Navigate to `website` directory:
   ```bash
   cd website
   ```
2. Install the nessecary dependencies:
   ```bash
   npm install
   ```

#### Development Sorcery
- Start the development server at `localhost:8080`:
  ```bash
  npm run dev
  ```

### Building and Running in Production Mode
To forge an optimized version of your app:
```bash
npm run build
npm run start
```

## License
This project is shielded by the GNU General Public License. Check the `LICENSE` file.

## Contact
[Just drop an email to pr.babayee@icloud.com](mailto:pr.babayee@icloud.com)

Get ready to be inspired, replicate this setup for your gym, and start tracking your own fitness journey in style!
