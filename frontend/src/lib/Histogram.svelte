<script lang="ts">
  import { durationHistogram, fmtDuration, type Session } from './stats';
  import { barPath, tipProps } from './tip.svelte';

  let { sessions, avg }: { sessions: Session[]; avg: number } = $props();

  let width = $state(500);
  const bins = $derived(durationHistogram(sessions));
  const H = 200, top = 18, bottom = 22, left = 8;
  const max = $derived(Math.max(1, ...bins.map((b) => b.count)));
  const y = (c: number) => top + (H - top - bottom) * (1 - c / max);
  const step = $derived((width - left) / bins.length);
  const bw = $derived(step - 2);
  const xAt = (min: number) => left + (min / 15) * step;
</script>

<div class="card">
  <div class="card-head">
    <h2>How long I stay</h2>
    <span class="sub">session length, 15 min bins</span>
  </div>
  <div bind:clientWidth={width}>
    <svg {width} height={H} role="group" aria-label="Distribution of session lengths">
      <line x1={left} x2={width} y1={y(0)} y2={y(0)} stroke="var(--grid)" />
      {#each bins as b, i}
        {@const x = left + i * step + 1}
        <path d={barPath(x, y(b.count), bw, y(0) - y(b.count))} fill="var(--accent)" />
        <rect
          class="hit"
          x={left + i * step}
          y={top}
          width={step}
          height={H - top - bottom}
          {...tipProps(i === bins.length - 1 ? `${b.from}+ min` : `${b.from}–${b.from + 15} min`, [`${b.count} session${b.count === 1 ? '' : 's'}`])}
        />
        {#if b.from % 60 === 0}
          <text x={x} y={H - 6}>{b.from / 60}h{i === bins.length - 1 ? '+' : ''}</text>
        {/if}
      {/each}
      {#if avg > 0}
        <line x1={xAt(Math.min(avg, 180))} x2={xAt(Math.min(avg, 180))} y1={top - 4} y2={y(0)} stroke="var(--text-2)" stroke-dasharray="4 4" />
        <text x={xAt(Math.min(avg, 180)) + 5} y={top + 6} class="avg">avg {fmtDuration(avg)}</text>
      {/if}
    </svg>
  </div>
</div>

<style>
  svg {
    display: block;
    overflow: visible;
  }
  .avg {
    fill: var(--text-2);
    font-weight: 600;
  }
</style>
