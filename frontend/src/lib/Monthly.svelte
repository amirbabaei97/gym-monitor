<script lang="ts">
  import { fmtDuration, monthly, MONTHS, type Session } from './stats';
  import { barPath, tipProps } from './tip.svelte';

  let { sessions, now }: { sessions: Session[]; now: Date } = $props();

  let width = $state(500);
  const data = $derived(monthly(sessions, now, 12));
  const H = 200, top = 18, bottom = 22, left = 26;
  // Hours when durations are known, visits otherwise (Fitness First reports check-ins only).
  const useHours = $derived(data.some((d) => d.minutes > 0));
  const val = (d: { visits: number; minutes: number }) => (useHours ? d.minutes / 60 : d.visits);
  const unit = $derived(useHours ? 'h' : '');
  const maxH = $derived(Math.max(4, ...data.map(val)));
  const niceMax = $derived(Math.ceil(maxH / 5) * 5);
  const y = (h: number) => top + (H - top - bottom) * (1 - h / niceMax);
  const step = $derived((width - left) / data.length);
  const bw = $derived(Math.min(36, step - 2));
  const best = $derived(data.reduce((a, d) => (val(d) > val(a) ? d : a), data[0]));
  const ticks = $derived([0, niceMax / 2, niceMax]);
</script>

<div class="card">
  <div class="card-head">
    <h2>{useHours ? 'Hours' : 'Visits'} per month</h2>
    <span class="sub">best: {MONTHS[best.month.getUTCMonth()]} {best.month.getUTCFullYear()}, {useHours ? fmtDuration(best.minutes) : `${best.visits} visits`}</span>
  </div>
  <div bind:clientWidth={width}>
    <svg {width} height={H} role="group" aria-label="Gym visits per month">
      {#each ticks as t}
        <line x1={left} x2={width} y1={y(t)} y2={y(t)} stroke="var(--grid)" />
        <text x={left - 6} y={y(t) + 4} text-anchor="end">{t}{unit}</text>
      {/each}
      {#each data as d, i}
        {@const h = val(d)}
        {@const x = left + i * step + (step - bw) / 2}
        <path d={barPath(x, y(h), bw, y(0) - y(h))} fill="var(--accent)" />
        {#if d === best && h > 0}
          <text x={x + bw / 2} y={y(h) - 5} text-anchor="middle" class="lbl">{Math.round(h)}{unit}</text>
        {/if}
        <rect
          class="hit"
          x={left + i * step}
          y={top}
          width={step}
          height={H - top - bottom}
          {...tipProps(`${MONTHS[d.month.getUTCMonth()]} ${d.month.getUTCFullYear()}${i === data.length - 1 ? ' (so far)' : ''}`, [
            `${d.visits} visit${d.visits === 1 ? '' : 's'}`,
            ...(useHours ? [fmtDuration(d.minutes)] : []),
          ])}
        />
        <text x={x + bw / 2} y={H - 6} text-anchor="middle">{MONTHS[d.month.getUTCMonth()].slice(0, width < 420 ? 1 : 3)}</text>
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
