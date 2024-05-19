<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/bulma/0.9.3/css/bulma.min.css">
<script>
    import {
        onMount
    } from 'svelte';
    import ChartComponent from './Chart.svelte';

    let data = [];
    let totalVisits = 0;
    let totalDuration = 0;
    let averageVisitsPerWeek = 0;
    let averageDurationPerVisit = 0;
    let goalVisitsPerWeek = 5;
    let progressTowardsGoal = 0;
    let startDate, endDate;
    let formattedDuration = "0 minutes";

    onMount(async () => {
        const today = new Date();
        const twoWeeksAgo = new Date(today.getTime() - (14 * 24 * 60 * 60 * 1000));
        startDate = twoWeeksAgo.toISOString().split('T')[0];
        endDate = today.toISOString().split('T')[0];

        await fetchData();
    });
    let allTimeData = [];

    async function fetchData() {
        // fetching data for the last two weeks
        try {
            const response = await fetch(
                `https://gym.amir.rocks/api/checkins/?start_date=${startDate}T00:00:00&end_date=${endDate}T23:59:59`);
            if (!response.ok) throw new Error('Network response was not ok');
            let newData = await response.json();
            if (!Array.isArray(newData)) throw new Error('Data received is not an array');

            data = newData;
            updateMetrics();
        } catch (error) {
            console.error("Failed to fetch data:", error.message);
            data = [];
        }
        // fetching all-time data
        try {
            const response = await fetch('https://gym.amir.rocks/api/checkins/');
            if (!response.ok) throw new Error('Network response was not ok');
            let newData = await response.json();
            if (!Array.isArray(newData)) throw new Error('Data received is not an array');

            allTimeData = newData;
            updateMetrics();
        } catch (error) {
            console.error("Failed to fetch all-time data:", error.message);
        }
    }

    function updateMetrics() {
        totalVisits = allTimeData.length;
        totalDuration = allTimeData.reduce((sum, item) => sum + Number(item.Duration), 0);
        if (totalDuration) {
            let seconds = Math.floor((totalDuration * 60) % 60);
            let minutes = Math.floor(totalDuration % 60);
            let hours = Math.floor((totalDuration / 60) % 24);
            let days = Math.floor(totalDuration / 1440);

            formattedDuration = `${days} days, ${hours} hrs, ${minutes} mins`;
        } else {
            formattedDuration = "0 minutes";
        }
        if (allTimeData.length > 0) {
            const startDate = new Date(allTimeData[0]["Start Time"]);
            const endDate = new Date(allTimeData[allTimeData.length - 1]["End Time"]);
            const millisecondsPerWeek = 7 * 24 * 60 * 60 * 1000 * -1;
            const weeks = Math.ceil((endDate - startDate) / millisecondsPerWeek);

            averageVisitsPerWeek = totalVisits / weeks;
            progressTowardsGoal = (totalVisits / (goalVisitsPerWeek * weeks)) * 100;
        } else {
            averageVisitsPerWeek = 0;
            progressTowardsGoal = 0;
        }
        averageDurationPerVisit = totalDuration / totalVisits || 0;

    }
    let quotes = ["Push yourself because no one else is going to do it for you.",
        "The only bad workout is the one that didn't happen.",
        "To enjoy the glow of good health, you must exercise.",
        "Strength doesn't come from what you can do. It comes from overcoming the things you once thought you couldn't.",
        "Sweat is just fat crying—keep it weeping!",
        "Fall in love with taking care of your body. It's the only place you have to live.",
        "Exercise not only changes your body; it changes your mind, your attitude, and your mood.",
        "Your workout is a celebration of what your body can do, not a punishment for what you ate."
    ];
    let quote = quotes[Math.floor(Math.random() * quotes.length)];
</script>


<main>
    <h1 class="title">Gym Wall of Shame</h1>
    <p>I’ve been slacking on my squats and skipping leg days, so I’ve launched my very own ‘Gym Wall of Shame’ online to
        keep myself in check!</p>
    {#if data.length > 0}
        <div class="cards">
            <div class="card">
                <header class="card-header">
                    <p class="card-header-title">Check-ins Log</p>
                </header>
                <div class="card-content">
                        <table>
                            <tr>
                                <th>Date</th>
                                <th>Time</th>
                                <th>Duration</th>
                            </tr>
                            {#each data as item}
                            <tr>
                                <td>{item["Start Time"].split(" ")[0]}</td>
                                <td>{item["Start Time"].split(" ")[1].slice(0,5)} to {item["End Time"].split(" ")[1].slice(0,5)}</td>
                                <td>{item.Duration} minutes</td>
                            </tr>
                            {/each}
                        </table>
                    </div>
                </div>
            <div class="card">
                <header class="card-header">
                    <p class="card-header-title">Metrics</p>
                </header>
                <div class="card-content">
                    <table style="width:100%">
                        <tr>
                          <th>Total Visits</th>
                          <td>{totalVisits} times</td>
                        </tr>
                        <tr>
                          <th>Average Visits Per Week</th>
                          <td>{averageVisitsPerWeek.toFixed(2)} times/week</td>
                        </tr>
                        <tr>
                            <th>Total Duration Spent</th>
                            <td>{formattedDuration}</td>
                        </tr>
                        <tr>
                            <th>Average Duration Per Visit</th>
                            <td>{averageDurationPerVisit.toFixed(2)} minutes</td>
                          </tr>
                          <tr>
                            <th>Progress Towards Weekly Goal</th>
                            <td>
                                {progressTowardsGoal.toFixed(2)}%
                                <progress value={progressTowardsGoal} max="100"></progress>
                            </td>
                        </tr>                        
                      </table>
                 </div>
            </div>
            <div class="card">
                <header class="card-header">
                    <p class="card-header-title">Durations</p>
                </header>
                <div class="card-content">
                    <div class="date-picker is-flex">
                        <div class="field">
                            <label class="label" for="start-date">Start Date:</label>
                            <div class="control">
                                <input id="start-date" class="input" type="date" bind:value={startDate} on:change={fetchData}>
                            </div>
                        </div>
                        <div class="field">
                            <label class="label" for="end-date">End Date:</label>
                            <div class="control">
                                <input id="end-date" class="input" type="date" bind:value={endDate} on:change={fetchData}>
                            </div>
                        </div>
                    </div>
                        {#if data.length > 0}
                        <ChartComponent {data} />
                    {:else}
                        <p>Pick the dates first!</p>
                    {/if}
                </div>
            </div>
        </div>
    {:else}
        <p>Pick the dates first!</p>
    {/if}
    <p class="motivational-quote"><b>Motivational quote of the day: </b>{quote}</p>
</main>

<style>
:global(body) {
    margin: 0; /* Remove default margin */
    padding: 0; /* Remove default padding */
    background-color: #FFDEB5; /* Light peach background */
    min-height: 10vh; /* Full viewport height */
}  
    :root {
    --primary-color: #8abce5; /* Sporty blue */
    --accent-color: #F44336; /* Energetic red */
    --text-color: #000000; /* White text for high contrast */
}
    .card-content {
        padding: 20px;
        text-align: left;
        border-radius: 5px;
    }
    main {
        font-family: 'Oswald', sans-serif;
        text-align: center;
        padding: 1em;
        margin: auto;
        display: flex; /* Use flexbox to enable flexible box layouts */
        flex-direction: column; /* Stack children vertically */
        justify-content: flex-start; /* Align children to the start of the main axis */
        align-items: center; /* Center children along the cross axis */
        min-height: calc(100vh - 60px); /* Full height minus footer height */
        padding-bottom: 60px; /* Space for the footer */

    }

    .cards {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
    }
    .date-picker {
        justify-content: space-around;
    }
    .card {
        margin: 1em;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        width: 100%;
        max-width: 400px; /* Consistent card size */
        border-radius: 5px;
        overflow: hidden;
        background-color: #FAD961;
background-image: linear-gradient(131deg, #FAD961 24%, #F76B1C 100%);

        

        color: var(--text-color);
        transform: rotate(0deg); /* Slight angle to create dynamic tension */
        transition: transform 0.1s ease;
    }
    .card:hover {
    transform: rotate(-5deg); /* Straightens on hover for interaction */
}
    .card-header {
        background-color: #FAD961;
        background-image: linear-gradient(323deg, #FAD961 0%, #F76B1C 0%);
        font-size: 1.2em;
    }
    .card-header-title {
        color: white;
    }
    table {
        width: 100%;
        table-layout: fixed; /* Better handling of table column width */
    }
    th, td {
        padding: 8px;
        text-align: left;
    }
    progress {
        width: 100%;
        height: 20px; /* Bigger and more visible */
        background-color: white;

    }
    footer {
        position: fixed;
        bottom: 0;
        width: 100%;
        max-height: 60px;
        color: white;
        padding: 0.5em;
        background-color: #FAD961;
        background-image: linear-gradient(323deg, #FAD961 0%, #F76B1C 0%);

    }
    .big-emoji {
        font-size: 1.5em;
    }
    @media (max-width: 768px) {
        .cards {
            flex-direction: column;
            align-items: center;
        }
    }
    @media (max-width: 400px) { /* Adjust this value based on when you want the change to occur */
        .card {
            max-width: 90vw; /* Consistent card size on smaller screens */
        }
    }
        @media (max-height: 668px) {
            :global(body) {
                min-height: 290vh; /* Remove space for the footer */
            }
        }

        @media (min-height: 669px) and (max-height: 896px) {
            :global(body) {
                min-height: 190vh; /* Adjust for larger screens like iPhone XR, iPhone 11, iPhone 11 Pro */
            }
        }

        @media (min-height: 897px) and (max-height: 926px) {
            :global(body) {
                min-height: 180; /* Adjust for larger screens like iPhone 12 Pro Max */
            }
        }

        @media (min-height: 927px) and (max-height: 1024px) {
            :global(body) {
                min-height: 140vh; /* Adjust for larger screens like iPads */
            }
        }
</style>
<!-- add a sticky footer here -->
<footer class="footer">
    <div class="content has-text-centered">
        <p>
            Created with <span class="big-emoji">💪</span> by <a href="https://amir.rocks">Amir</a>.
        </p>
    </div>
</footer>