<script>
    import { onMount, onDestroy, afterUpdate } from 'svelte';
    import Chart from 'chart.js/auto';

    export let data = [];

    let chart = null;
    let chartContainer;

    function createChart() {
        if (chartContainer && data.length > 0) {
            const ctx = chartContainer.getContext('2d');
            if (chart) {
                chart.destroy(); // Destroy the existing chart if it exists
            }
            chart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: data.map(item => new Date(item["Start Time"]).toLocaleDateString()),
                    datasets: [{
                        label: 'Duration (minutes)',
                        data: data.map(item => parseInt(item.Duration)),
                        backgroundColor: 'rgba(238, 238, 238, 0.6)',
                        borderColor: 'rgba(189, 195, 199, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
        }
    }

    onMount(createChart);

    // Update chart whenever data changes
    afterUpdate(createChart);

    onDestroy(() => {
        if (chart) {
            chart.destroy();
        }
    });
</script>

<canvas bind:this={chartContainer}></canvas>
