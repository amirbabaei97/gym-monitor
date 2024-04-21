<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/bulma/0.9.3/css/bulma.min.css">

<script>
    import { onMount } from 'svelte';
    import ChartComponent from './Chart.svelte';

    let data = [];
    let startDate = '';
    let endDate = '';

    async function fetchData() {
        try {
            const response = await fetch(`http://localhost:8000/checkins/?start_date=${startDate}T00:00:00&end_date=${endDate}T23:59:59`);
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            const newData = await response.json();
            if (!Array.isArray(newData)) {
                throw new Error('Data received is not an array');
            }
            data = [...newData]; // This will only execute if newData is an array
        } catch (error) {
            console.error("Failed to fetch data:", error.message);
            data = []; // Reset data or handle error state appropriately
        }
    }

    onMount(() => {
        fetchData();
    });
</script>



<main>
    <h1>Amir's Gym check-ins!</h1>
    <h3>Pick the dates to start:</h3>
    <div class="date-picker">
        <input type="date" bind:value={startDate} on:change={fetchData}>
        <input type="date" bind:value={endDate} on:change={fetchData}>
    </div>
    <!-- Check if data is loaded and then display -->
    {#if data.length > 0}
        <div class="cards">
            {#each data as item}
                <div class="card">
                    <header class="card-header">
                        <p class="card-header-title">{item.Studio}</p>
                    </header>
                    <div class="card-content">
                        <div class="content">
                            Date: {item["Start Time"].split(" ")[0]}<br>
                            Time: from {item["Start Time"].split(" ")[1]} to {item["End Time"].split(" ")[1]}<br>
                            Duration: {item.Duration} minutes
                        </div>
                    </div>
                </div>
            {/each}
        </div>
    {:else}
        <p>Pick the dates first!</p>
    {/if}
    <h3>Your Bar Chart:</h3>
    {#if data.length > 0}
        <ChartComponent {data} />
    {:else}
        <p>Pick the dates first!</p>
    {/if}
</main>

<style>
    main {
        text-align: center;
        padding: 1em;
        margin: 0 auto;
    }

    .cards {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
    }

    .card {
        margin: 0.5em;
        box-shadow: 0 2px 3px rgba(0,0,0,0.1);
        width: 300px;
    }

    h1 {
        color: #ff3e00;
        text-transform: uppercase;
        font-size: 4em;
        font-weight: 100;
    }

    h3 {
        color: #1492d2;
        font-size: 2em;
        font-weight: 100;
        text-align: left;
    }

    @media (min-width: 640px) {
        main {
            max-width: none;
        }
    }
</style>
