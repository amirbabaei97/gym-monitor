<script lang="ts">
  import { fmtDate, hhmm, shame, type Session } from './stats';

  interface Props {
    daysSince: number | null;
    last: Session | null;
    thisWeek: number;
    goal: number;
    streak: { current: number; best: number; currentIncludesThisWeek: boolean };
    live: { since: Date } | null;
    now: Date;
  }
  let { daysSince, last, thisWeek, goal, streak, live, now }: Props = $props();

  const s = $derived(live ? { level: 0, label: 'In the gym right now', emoji: '🏋️', blurb: 'Lifting things up and putting them down.' } : shame(daysSince));
  const statusVar = $derived(['--good', '--good', '--warning', '--serious', '--critical'][s.level]);
  const pct = $derived(Math.min(1, thisWeek / goal));
  const R = 52;
  const C = 2 * Math.PI * R;
  const daysLeft = $derived(7 - ((now.getUTCDay() + 6) % 7)); // incl. today
  const liveMin = $derived(live ? Math.max(0, Math.round((now.getTime() - live.since.getTime()) / 60000)) : 0);
</script>

<section class="hero card" style:--status="var({statusVar})">
  <div class="shame">
    <div class="eyebrow">
      <span class="dot" class:pulse={live}></span>
      {live ? 'Live' : 'Days since last gym visit'}
    </div>
    {#if live}
      <div class="big num">{liveMin}<small>min</small></div>
      <p class="meta">Checked in at {hhmm(live.since)}</p>
    {:else}
      <div class="big num">{daysSince ?? '–'}</div>
      {#if last}
        <p class="meta">Last seen {fmtDate(last.start)}, {hhmm(last.start)}{last.end ? `–${hhmm(last.end)}` : ''}</p>
      {/if}
    {/if}
    <div class="verdict">
      <span class="chip"><span aria-hidden="true">{s.emoji}</span> {s.label}</span>
      <span class="blurb">{s.blurb}</span>
    </div>
    <div class="meter" role="meter" aria-label="Shame level" aria-valuemin="0" aria-valuemax="4" aria-valuenow={s.level}>
      {#each [0, 1, 2, 3, 4] as i}<span class:on={i <= s.level}></span>{/each}
    </div>
  </div>

  <div class="side">
    <div class="ring-wrap">
      <svg viewBox="0 0 128 128" class="ring" aria-label="{thisWeek} of {goal} visits this week" role="img">
        <circle cx="64" cy="64" r={R} class="track" />
        {#if pct > 0}
          <circle
            cx="64"
            cy="64"
            r={R}
            class="fill"
            stroke-dasharray="{C * pct} {C}"
            transform="rotate(-90 64 64)"
          />
        {/if}
      </svg>
      <div class="ring-label">
        <span class="num">{thisWeek}<small>/{goal}</small></span>
        <span>this week</span>
      </div>
    </div>
    <div class="side-stats">
      <div>
        <span class="num">{streak.current}</span>
        <span class="lbl">week streak {streak.current >= 3 ? '🔥' : ''}</span>
      </div>
      <div>
        <span class="num">{streak.best}</span>
        <span class="lbl">best streak</span>
      </div>
      <div>
        <span class="num">{thisWeek >= goal ? '✓' : `${goal - thisWeek}`}</span>
        <span class="lbl">{thisWeek >= goal ? 'goal met' : `to go, ${daysLeft} day${daysLeft === 1 ? '' : 's'} left`}</span>
      </div>
    </div>
  </div>
</section>

<style>
  .hero {
    display: grid;
    grid-template-columns: 1.3fr 1fr;
    gap: 28px;
    padding: 28px;
    position: relative;
    overflow: hidden;
    background:
      radial-gradient(120% 140% at 0% 0%, var(--accent-glow), transparent 55%),
      var(--surface);
  }
  .eyebrow {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--text-2);
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--status);
  }
  .pulse {
    animation: pulse 1.6s ease-out infinite;
  }
  @keyframes pulse {
    0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--status) 60%, transparent); }
    100% { box-shadow: 0 0 0 10px transparent; }
  }
  .big {
    font-size: clamp(5rem, 16vw, 9rem);
    font-weight: 700;
    line-height: 0.95;
    margin: 10px 0 6px;
  }
  .big small {
    font-size: 0.3em;
    margin-left: 8px;
    color: var(--text-2);
    font-weight: 500;
  }
  .meta {
    color: var(--text-2);
    margin: 0 0 16px;
  }
  .verdict {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 10px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 12px;
    border-radius: 999px;
    font-weight: 600;
    font-size: 0.9rem;
    background: color-mix(in srgb, var(--status) 16%, transparent);
    border: 1px solid color-mix(in srgb, var(--status) 45%, transparent);
  }
  .blurb {
    color: var(--text-2);
    font-size: 0.9rem;
  }
  .meter {
    display: flex;
    gap: 4px;
    margin-top: 18px;
    max-width: 260px;
  }
  .meter span {
    flex: 1;
    height: 6px;
    border-radius: 3px;
    background: var(--surface-2);
  }
  .meter span.on {
    background: var(--status);
  }
  .side {
    display: flex;
    align-items: center;
    gap: 24px;
    justify-content: flex-end;
  }
  .ring-wrap {
    position: relative;
    width: 150px;
    flex: none;
  }
  .ring {
    width: 100%;
    display: block;
  }
  .track {
    fill: none;
    stroke: var(--surface-2);
    stroke-width: 12;
  }
  .fill {
    fill: none;
    stroke: var(--accent);
    stroke-width: 12;
    stroke-linecap: round;
    transition: stroke-dasharray 0.8s cubic-bezier(0.2, 0.8, 0.2, 1);
  }
  .ring-label {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: var(--text-2);
    font-size: 0.78rem;
  }
  .ring-label .num {
    font-size: 2.2rem;
    font-weight: 700;
    color: var(--text);
    line-height: 1;
  }
  .ring-label small {
    font-size: 0.5em;
    color: var(--muted);
  }
  .side-stats {
    display: grid;
    gap: 12px;
  }
  .side-stats div {
    display: flex;
    flex-direction: column;
  }
  .side-stats .num {
    font-size: 1.6rem;
    font-weight: 700;
    line-height: 1.1;
  }
  .lbl {
    color: var(--muted);
    font-size: 0.8rem;
  }
  @media (max-width: 760px) {
    .hero {
      grid-template-columns: 1fr;
      padding: 22px;
    }
    .side {
      justify-content: flex-start;
    }
    .ring-wrap {
      width: 124px;
    }
  }
</style>
