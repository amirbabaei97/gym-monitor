<script lang="ts">
  import { punchCard, WEEKDAYS, type Session } from './stats';
  import { tipProps } from './tip.svelte';

  let { sessions }: { sessions: Session[] } = $props();

  let width = $state(500);
  const grid = $derived(punchCard(sessions));
  // Only show the hours that ever had a check-in (plus a margin), so the grid isn't mostly night.
  const hours = $derived.by(() => {
    const used = grid[0].map((_, h) => grid.some((r) => r[h] > 0));
    let a = used.indexOf(true), b = used.lastIndexOf(true);
    if (a < 0) [a, b] = [6, 22];
    return Array.from({ length: b - a + 1 }, (_, i) => a + i);
  });
  const max = $derived(Math.max(1, ...grid.flat()));
  const left = 34, top = 4, bottom = 20;
  const step = $derived((width - left) / hours.length);
  const row = 26;
  const H = top + 7 * row + bottom;
  const level = (c: number) => (c === 0 ? 0 : Math.min(4, 1 + Math.floor((c / max) * 3.999)));
</script>

<div class="card">
  <div class="card-head">
    <h2>When I check in</h2>
    <span class="sub">by weekday and hour</span>
  </div>
  <div bind:clientWidth={width}>
    <svg {width} height={H} role="group" aria-label="Check-ins by weekday and hour">
      {#each WEEKDAYS as d, r}
        <text x={left - 8} y={top + r * row + row / 2 + 4} text-anchor="end">{d}</text>
        {#each hours as h, c}
          {@const n = grid[r][h]}
          {@const rad = n ? 3 + (Math.min(step, row) / 2 - 4) * Math.sqrt(n / max) : 2}
          <circle cx={left + c * step + step / 2} cy={top + r * row + row / 2} r={Math.max(2, rad)} fill="var(--seq-{level(n)})" />
          <rect
            class="hit"
            x={left + c * step}
            y={top + r * row}
            width={step}
            height={row}
            {...tipProps(`${d} ${String(h).padStart(2, '0')}:00–${String(h + 1).padStart(2, '0')}:00`, [`${n} check-in${n === 1 ? '' : 's'}`])}
          />
        {/each}
      {/each}
      {#each hours as h, c}
        {#if h % 3 === 0}
          <text x={left + c * step + step / 2} y={H - 4} text-anchor="middle">{h}h</text>
        {/if}
      {/each}
    </svg>
  </div>
</div>

<style>
  svg {
    display: block;
  }
</style>
