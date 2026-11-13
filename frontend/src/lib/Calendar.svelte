<script lang="ts">
  import { calendar, fmtDateY, fmtDuration, MONTHS, type Session } from './stats';
  import { tipProps } from './tip.svelte';

  let { sessions, now }: { sessions: Session[]; now: Date } = $props();

  let width = $state(800);
  const left = 28, top = 18;
  const weeks = $derived(width < 560 ? 26 : 53);
  const cols = $derived(calendar(sessions, now, weeks));
  const gap = 3;
  const cell = $derived(Math.max(8, Math.min(16, Math.floor((width - left) / weeks) - gap)));
  const H = $derived(top + 7 * (cell + gap));
  const visitDays = $derived(cols.flat().filter((d) => d.visits > 0 && !d.future).length);
  // Shade by time spent when durations are known; Fitness First only reports check-ins, so then by visits.
  const timed = $derived(sessions.some((s) => s.minutes));
  const level = (d: { minutes: number; visits: number }) =>
    timed
      ? (d.minutes === 0 ? 0 : d.minutes < 50 ? 1 : d.minutes < 75 ? 2 : d.minutes < 100 ? 3 : 4)
      : d.visits === 0 ? 0 : d.visits === 1 ? 2 : 4;
</script>

<div class="card">
  <div class="card-head">
    <h2>The gym calendar</h2>
    <span class="sub">{visitDays} gym days in the last {weeks === 53 ? '12 months' : '6 months'}</span>
  </div>
  <div bind:clientWidth={width} class="wrap">
    <svg width={left + weeks * (cell + gap)} height={H} role="group" aria-label="Gym visits per day">
      {#each ['Mon', '', 'Wed', '', 'Fri', '', ''] as l, i}
        {#if l}<text x={left - 6} y={top + i * (cell + gap) + cell - 2} text-anchor="end">{l}</text>{/if}
      {/each}
      {#each cols as col, w}
        {#if col[0].date.getUTCDate() <= 7}
          <text x={left + w * (cell + gap)} y={top - 6}>{MONTHS[col[0].date.getUTCMonth()]}</text>
        {/if}
        {#each col as d, i}
          {#if !d.future}
            <rect
              x={left + w * (cell + gap)}
              y={top + i * (cell + gap)}
              width={cell}
              height={cell}
              rx="3"
              fill="var(--seq-{level(d)})"
              {...tipProps(fmtDateY(d.date), d.visits ? [timed ? `${d.visits > 1 ? d.visits + ' visits, ' : ''}${fmtDuration(d.minutes)}` : `${d.visits} check-in${d.visits > 1 ? 's' : ''}`] : ['Skipped 🫠'])}
            />
          {/if}
        {/each}
      {/each}
    </svg>
  </div>
  {#if timed}
    <div class="legend scale">
      <span>Less</span>
      {#each [0, 1, 2, 3, 4] as i}<i style:background="var(--seq-{i})"></i>{/each}
      <span>More time</span>
    </div>
  {:else}
    <div class="legend scale">
      <span><i style:background="var(--seq-0)"></i>No visit</span>
      <span><i style:background="var(--seq-2)"></i>Check-in</span>
      <span><i style:background="var(--seq-4)"></i>2+ check-ins</span>
    </div>
  {/if}
</div>

<style>
  .wrap {
    overflow: hidden;
  }
  svg {
    display: block;
  }
  .scale {
    margin-top: 10px;
    gap: 4px;
    justify-content: flex-end;
  }
  .scale i {
    margin: 0;
  }
  .scale span {
    margin: 0 4px;
  }
</style>
