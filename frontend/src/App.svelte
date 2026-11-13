<script lang="ts">
  import { onMount } from 'svelte';
  import Calendar from './lib/Calendar.svelte';
  import Hero from './lib/Hero.svelte';
  import Histogram from './lib/Histogram.svelte';
  import Monthly from './lib/Monthly.svelte';
  import PunchCard from './lib/PunchCard.svelte';
  import SessionLog from './lib/SessionLog.svelte';
  import Tile from './lib/Tile.svelte';
  import Tooltip from './lib/Tooltip.svelte';
  import WeekdayBars from './lib/WeekdayBars.svelte';
  import WeeklyBars from './lib/WeeklyBars.svelte';
  import {
    bestWeek, daysBetween, fmtDate, fmtDateY, fmtDuration, hhmm, inRange, longestGap, monthToDate, parse,
    RANGES, startOfWeek, streaks, summary, toSessions, type Dashboard, type Range,
  } from './lib/stats';
  import { QUOTES } from './lib/quotes';

  let dash = $state<Dashboard | null>(null);
  let error = $state('');
  let range = $state<Range>(readPref("range", "all") as Range);
  let theme = $state(readPref('theme', ''));
  let etag = '';

  function readPref(key: string, fallback: string) {
    try { return localStorage.getItem('gym.' + key) ?? fallback; } catch { return fallback; }
  }
  function writePref(key: string, value: string) {
    try { localStorage.setItem('gym.' + key, value); } catch { /* private mode */ }
  }

  async function load() {
    try {
      const r = await fetch('/api/dashboard', { headers: etag ? { 'If-None-Match': etag } : {} });
      if (r.status === 304) return;
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      etag = r.headers.get('ETag') ?? '';
      dash = await r.json();
      error = '';
    } catch (e) {
      error = 'Could not load the data. The server is probably skipping leg day.';
    }
  }

  onMount(() => {
    load();
    const t = setInterval(load, 5 * 60_000);
    const onVis = () => document.visibilityState === 'visible' && load();
    document.addEventListener('visibilitychange', onVis);
    return () => { clearInterval(t); document.removeEventListener('visibilitychange', onVis); };
  });

  $effect(() => {
    if (theme) document.documentElement.dataset.theme = theme;
    else delete document.documentElement.dataset.theme;
    writePref('theme', theme);
  });
  $effect(() => writePref('range', range));

  function toggleTheme() {
    const dark = theme ? theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
    theme = dark ? 'light' : 'dark';
  }

  const now = $derived(dash ? parse(dash.now) : new Date());
  const all = $derived(dash ? toSessions(dash.sessions) : []);
  const scoped = $derived(inRange(all, range, now));
  const last = $derived(all.at(-1) ?? null);
  const live = $derived(dash?.live ? { since: parse(dash.live.since) } : null);
  const goal = $derived(dash?.weeklyGoal ?? 3);
  const thisWeek = $derived(all.filter((s) => s.start >= startOfWeek(now)).length + (live ? 1 : 0));
  const streak = $derived(streaks(all, now, goal));
  const sum = $derived(summary(scoped, now, range));
  const mtd = $derived(monthToDate(all, now));
  const daysSince = $derived(last ? daysBetween(last.start, now) : null);
  const timed = $derived(scoped.some((s) => s.minutes));
  const gap = $derived(longestGap(scoped, now));
  const best = $derived(bestWeek(scoped));
  const minuteOfDay = (d: Date) => d.getUTCHours() * 60 + d.getUTCMinutes();
  const latest = $derived(scoped.reduce<(typeof scoped)[number] | null>((a, s) => (!a || minuteOfDay(s.start) > minuteOfDay(a.start) ? s : a), null));
  const rangeLabel = $derived(RANGES.find((r) => r.id === range)!.label.toLowerCase());
  const quote = QUOTES[Math.floor(Math.random() * QUOTES.length)];

  function ago(iso: string | null) {
    if (!iso) return 'never';
    const min = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
    if (min < 1) return 'just now';
    if (min < 60) return `${min} min ago`;
    if (min < 48 * 60) return `${Math.round(min / 60)} h ago`;
    return `${Math.round(min / 1440)} days ago`;
  }
  const syncNote = $derived.by(() => {
    const s = dash?.sync;
    if (!s?.state) return 'Not synced yet';
    if (s.state === 'ok') return `Synced with Fitness First ${ago(s.last_ok)}`;
    if (s.state === 'auth_expired') return `Fitness First login expired — data as of ${ago(s.last_ok)}`;
    if (s.state === 'not_configured') return 'Fitness First not connected yet';
    if (s.state === 'login_rejected') return `Fitness First login rejected — data as of ${ago(s.last_ok)}`;
    return `Last sync failed — data as of ${ago(s.last_ok)}`;
  });
</script>

<svelte:head><title>{dash?.title ?? 'Gym Wall of Shame'}</title></svelte:head>

<div class="page">
  <header>
    <div>
      <h1>{dash?.title ?? 'Gym Wall of Shame'}<span class="flex" aria-hidden="true">💪</span></h1>
      <p class="tag">I kept skipping leg day, so now every check-in at my gym is public. Judge accordingly.</p>
    </div>
    <button class="icon" onclick={toggleTheme} aria-label="Toggle dark mode" title="Toggle dark mode">◐</button>
  </header>

  {#if error && !dash}
    <div class="card notice">{error}</div>
  {:else if !dash}
    <div class="card notice skeleton">Counting reps…</div>
  {:else}
    <Hero {daysSince} {last} {thisWeek} {goal} {streak} {live} {now} />

    <nav class="filters" aria-label="Time range">
      {#each RANGES as r}
        <button class:active={range === r.id} aria-pressed={range === r.id} onclick={() => (range = r.id)}>{r.label}</button>
      {/each}
      <span class="sync" class:bad={dash.sync.state !== 'ok'}>{syncNote}</span>
    </nav>

    <section class="tiles">
      <Tile label="Check-ins" value={String(sum.visits)} note={rangeLabel} />
      <Tile label="Visits per week" value={sum.perWeek.toFixed(1)} unit="/wk" note={`goal ${goal}/wk`} delta={sum.visits ? sum.perWeek - goal : null} />
      <Tile label={`${mtd.label} so far`} value={String(mtd.cur)} unit="visits" note={`${mtd.prev} by this day last month`} delta={mtd.cur - mtd.prev} />
      <Tile label="Longest break" value={gap ? String(gap.days) : '0'} unit="days" note={gap ? (gap.ongoing ? 'still going 🫣' : `${fmtDate(gap.from)} → ${fmtDate(gap.to)}`) : 'never skipped'} />
      <Tile label="Best week" value={best ? String(best.visits) : '0'} unit="visits" note={best ? `week of ${fmtDateY(best.week)}` : ''} />
      <Tile label="Favourite slot" value={sum.favHour !== null ? `${String(sum.favHour).padStart(2, '0')}:00` : '–'} note={`${sum.favDay}s are the busiest`} />
      <Tile label="Earliest check-in" value={sum.earliest ? hhmm(sum.earliest.start) : '–'} note={sum.earliest ? fmtDateY(sum.earliest.start) : ''} />
      {#if timed}
        <Tile label="Average session" value={fmtDuration(sum.avgMin)} note={`${(sum.totalMin / 60).toFixed(0)} h in total`} />
      {:else}
        <Tile label="Latest check-in" value={latest ? hhmm(latest.start) : '–'} note={latest ? fmtDateY(latest.start) : ''} />
      {/if}
    </section>

    <div class="grid">
      <div class="span2"><Calendar sessions={all} {now} /></div>
      <WeeklyBars sessions={all} {now} {goal} />
      <Monthly sessions={all} {now} />
      <PunchCard sessions={scoped} />
      {#if timed}
        <Histogram sessions={scoped} avg={sum.avgMin} />
      {:else}
        <WeekdayBars sessions={scoped} />
      {/if}
      <div class="span2"><SessionLog sessions={scoped} {all} /></div>
    </div>

    <blockquote class="card quote">
      <span aria-hidden="true">“</span>{quote}
    </blockquote>
  {/if}

  <footer>
    Made with 💪 and mild guilt by <a href="https://amir.rocks">Amir</a> ·
    <a href="https://github.com/amirbabaei97/gym-monitor">source</a>
  </footer>
</div>

<Tooltip />

<style>
  .page {
    max-width: 1180px;
    margin: 0 auto;
    padding: 32px 16px 48px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
    margin-bottom: 8px;
  }
  h1 {
    font-size: clamp(1.9rem, 5vw, 2.8rem);
    font-weight: 700;
    line-height: 1.05;
  }
  .flex {
    display: inline-block;
    margin-left: 10px;
    transform-origin: 70% 70%;
    animation: flex 2.8s ease-in-out infinite;
  }
  @keyframes flex {
    0%, 80%, 100% { transform: rotate(0); }
    85% { transform: rotate(-14deg); }
    90% { transform: rotate(10deg); }
  }
  .tag {
    color: var(--text-2);
    margin: 8px 0 0;
    max-width: 60ch;
  }
  .icon {
    flex: none;
    width: 40px;
    height: 40px;
    border-radius: 12px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text);
    font-size: 1.1rem;
    cursor: pointer;
  }
  .filters {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }
  .filters button {
    font: inherit;
    font-size: 0.85rem;
    padding: 6px 14px;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--text-2);
    cursor: pointer;
  }
  .filters button.active {
    background: var(--text);
    border-color: var(--text);
    color: var(--bg);
  }
  .sync {
    margin-left: auto;
    color: var(--muted);
    font-size: 0.8rem;
  }
  .sync::before {
    content: '';
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--good);
    margin-right: 6px;
    vertical-align: 1px;
  }
  .sync.bad::before {
    background: var(--warning);
  }
  .tiles {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }
  .span2 {
    grid-column: span 2;
    min-width: 0;
  }
  .quote {
    margin: 0;
    font-family: var(--display);
    font-size: 1.15rem;
    color: var(--text-2);
    position: relative;
    padding-left: 48px;
  }
  .quote span {
    position: absolute;
    left: 16px;
    top: 4px;
    font-size: 3rem;
    color: var(--accent);
    line-height: 1;
  }
  .notice {
    color: var(--text-2);
  }
  .skeleton {
    animation: fade 1.2s ease-in-out infinite alternate;
  }
  @keyframes fade {
    to { opacity: 0.5; }
  }
  footer {
    text-align: center;
    color: var(--muted);
    font-size: 0.85rem;
    margin-top: 12px;
  }
  footer a {
    color: var(--accent-ink);
  }
  @media (max-width: 900px) {
    .tiles {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .grid {
      grid-template-columns: minmax(0, 1fr);
    }
    .span2 {
      grid-column: auto;
    }
  }
  @media (max-width: 520px) {
    .sync {
      margin-left: 0;
      width: 100%;
    }
  }
</style>
