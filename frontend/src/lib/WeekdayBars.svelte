<script lang="ts">
  import { weekdayCounts, WEEKDAYS, WEEKDAYS_LONG, type Session } from './stats';
  import { barPath, tipProps } from './tip.svelte';

  let { sessions }: { sessions: Session[] } = $props();

  let width = $state(500);
  const counts = $derived(weekdayCounts(sessions));
  const total = $derived(counts.reduce((a, b) => a + b, 0));
  const max = $derived(Math.max(1, ...counts));
  const H = 200, top = 18, bottom = 22, left = 4;
  const y = (c: number) => top + (H - top - bottom) * (1 - c / max);
  const step = $derived((width - left) / 7);
  const bw = $derived(Math.min(44, step - 2));
  const fav = $derived(counts.indexOf(max));
  const lazy = $derived(counts.indexOf(Math.min(...counts)));
</script>

<div class="card">
  <div class="card-head">
    <h2>Favourite days</h2>
    <span class="sub">{total ? `${WEEKDAYS_LONG[lazy]}s are the laziest` : 'no check-ins in range'}</span>
  </div>
  <div bind:clientWidth={width}>
    <svg {width} height={H} role="group" aria-label="Check-ins by weekday">
      <line x1={left} x2={width} y1={y(0)} y2={y(0)} stroke="var(--grid)" />
      {#each counts as n, i}
        {@const x = left + i * step + (step - bw) / 2}
        <path d={barPath(x, y(n), bw, y(0) - y(n))} fill="var(--accent)" />
        {#if i === fav && n > 0}
          <text x={x + bw / 2} y={y(n) - 5} text-anchor="middle" class="lbl">{n}</text>
        {/if}
        <rect
          class="hit"
          x={left + i * step}
          y={top}
          width={step}
          height={H - top - bottom}
          {...tipProps(`${WEEKDAYS_LONG[i]}s`, [`${n} check-in${n === 1 ? '' : 's'}`, total ? `${Math.round((n / total) * 100)}% of all` : ''])}
        />
        <text x={x + bw / 2} y={H - 6} text-anchor="middle">{WEEKDAYS[i]}</text>
      {/each}
    </svg>
  </div>
</div>

<style>
  svg {
    display: block;
    overflow: visible;
  }
  .lbl {
    fill: var(--text);
    font-weight: 600;
  }
</style>
