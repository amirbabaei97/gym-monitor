<script lang="ts">
  import { daysBetween, fmtDate, fmtDuration, hhmm, type Session } from './stats';

  let { sessions, all }: { sessions: Session[]; all: Session[] } = $props();
  let limit = $state(12);
  const rows = $derived([...sessions].reverse());
  const hasStudio = $derived(rows.some((s) => s.studio));
  const timed = $derived(rows.some((s) => s.minutes));

  // Days since the previous check-in (looked up in the full history, so the
  // first row of a filtered range still gets its gap).
  const gapOf = $derived.by(() => {
    const m = new Map<Session, number | null>();
    all.forEach((s, i) => m.set(s, i ? daysBetween(all[i - 1].start, s.start) : null));
    return m;
  });
  const shown = $derived(rows.slice(0, limit));
  const maxBar = $derived(
    timed ? Math.max(60, ...shown.map((s) => s.minutes ?? 0)) : Math.max(7, ...shown.map((s) => gapOf.get(s) ?? 0)),
  );
  const gapText = (d: number | null) =>
    d === null ? 'first one' : d === 0 ? 'same day' : d === 1 ? 'next day' : `${d} days later`;
</script>

<div class="card">
  <div class="card-head">
    <h2>Check-in log</h2>
    <span class="sub">{sessions.length} check-ins in range</span>
  </div>
  {#if rows.length}
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>{timed ? 'Time' : 'Checked in'}</th>
          {#if hasStudio}<th class="studio">Studio</th>{/if}
          <th class="bar-col">{timed ? 'Duration' : 'Since the last one'}</th>
        </tr>
      </thead>
      <tbody>
        {#each shown as s}
          {@const gap = gapOf.get(s) ?? null}
          {@const v = timed ? (s.minutes ?? 0) : (gap ?? 0)}
          <tr>
            <td>{fmtDate(s.start)} <span class="yr">{s.start.getUTCFullYear()}</span></td>
            <td class="num t">{hhmm(s.start)}{#if timed}–{s.end ? hhmm(s.end) : '??'}{/if}</td>
            {#if hasStudio}<td class="studio">{s.studio ?? ''}</td>{/if}
            <td class="bar-col">
              <span class="bar" class:warn={!timed && v >= 4} style:width="{Math.max(2, (v / maxBar) * 100)}%"></span>
              <span class="num">{timed ? (s.minutes ? fmtDuration(s.minutes) : '–') : gapText(gap)}</span>
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
    {#if rows.length > limit}
      <button onclick={() => (limit += 25)}>Show more</button>
    {/if}
  {:else}
    <p class="empty">Nothing in this range. Shameful.</p>
  {/if}
</div>

<style>
  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }
  th {
    text-align: left;
    color: var(--muted);
    font-weight: 500;
    font-size: 0.78rem;
    padding: 0 8px 8px 0;
    border-bottom: 1px solid var(--border);
  }
  td {
    padding: 9px 8px 9px 0;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  tr:last-child td {
    border-bottom: 0;
  }
  .yr {
    color: var(--muted);
  }
  .t {
    color: var(--text-2);
  }
  .bar-col {
    width: 42%;
  }
  .bar {
    display: inline-block;
    height: 6px;
    border-radius: 3px;
    background: var(--accent);
    margin-right: 8px;
    vertical-align: middle;
    max-width: calc(100% - 100px);
  }
  .bar.warn {
    background: var(--critical);
  }
  .studio {
    color: var(--text-2);
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 180px;
  }
  button {
    margin-top: 12px;
    background: var(--surface-2);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 7px 14px;
    font: inherit;
    font-size: 0.85rem;
    cursor: pointer;
  }
  .empty {
    color: var(--muted);
  }
  @media (max-width: 520px) {
    .studio,
    .yr {
      display: none;
    }
  }
</style>
