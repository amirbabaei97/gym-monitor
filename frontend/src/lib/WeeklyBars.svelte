<script lang="ts">
  import { addDays, fmtDuration, MONTHS, weeklyCounts, type Session } from './stats';
  import { barPath, tipProps } from './tip.svelte';

  let { sessions, now, goal }: { sessions: Session[]; now: Date; goal: number } = $props();

  let width = $state(600);
  const weeks = $derived(width < 520 ? 16 : 26);
  const data = $derived(weeklyCounts(sessions, now, weeks));
  const H = 200, top = 14, bottom = 24, left = 22;
  const max = $derived(Math.max(goal + 1, ...data.map((d) => d.visits)));
  const y = (v: number) => top + (H - top - bottom) * (1 - v / max);
  const step = $derived((width - left) / data.length);
  const bw = $derived(Math.max(4, step - 2)); // 2px gap between adjacent bars
  const met = $derived(data.filter((d) => d.visits >= goal).length);
  const ticks = $derived(Array.from({ length: max + 1 }, (_, i) => i).filter((t) => max <= 6 || t % 2 === 0));
  const fmtWeek = (d: Date) => `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
</script>

<div class="card">
  <div class="card-head">
    <h2>Visits per week</h2>
    <div class="legend">
      <span><i style:background="var(--accent)"></i>Goal met</span>
      <span><i style:background="var(--bar-muted)"></i>Missed</span>
      <span class="sub">{met} of {data.length} weeks on target</span>
    </div>
  </div>
  <div bind:clientWidth={width}>
    <svg {width} height={H} role="group" aria-label="Visits per week, last {weeks} weeks">
      {#each ticks as t}
        <line x1={left} x2={width} y1={y(t)} y2={y(t)} stroke="var(--grid)" />
        <text x={left - 6} y={y(t) + 4} text-anchor="end">{t}</text>
      {/each}
      {#each data as d, i}
        {@const x = left + i * step + (step - bw) / 2}
        {@const current = i === data.length - 1}
        <path
          d={barPath(x, y(d.visits), bw, y(0) - y(d.visits))}
          fill={d.visits >= goal ? 'var(--accent)' : 'var(--bar-muted)'}
        />
        <rect
          class="hit"
          x={left + i * step}
          y={top}
          width={step}
          height={H - top - bottom}
          {...tipProps(`${current ? 'This week' : 'Week of ' + fmtWeek(d.week)}`, [
            `${d.visits} visit${d.visits === 1 ? '' : 's'}`,
            d.minutes ? fmtDuration(d.minutes) + ' total' : 'no time logged',
          ])}
        />
        {#if d.week.getUTCDate() <= 7}
          <text x={x + bw / 2} y={H - 6} text-anchor="middle">{MONTHS[addDays(d.week, 6).getUTCMonth()]}</text>
        {/if}
      {/each}
      <line x1={left} x2={width} y1={y(goal)} y2={y(goal)} stroke="var(--text-2)" stroke-dasharray="4 4" />
      <text x={width - 2} y={y(goal) - 5} text-anchor="end" class="goal">goal {goal}</text>
    </svg>
  </div>
</div>

<style>
  svg {
    display: block;
    overflow: visible;
  }
  .goal {
    fill: var(--text-2);
    font-weight: 600;
  }
</style>
