// All times arrive as naive local wall-clock strings ("2026-11-05T19:35:26",
// in the gym's time zone). They are parsed as if UTC and read back with
// getUTC*, so the viewer's own time zone never shifts a visit to another day.

export interface RawSession { start: string; end: string | null; minutes: number | null; studio?: string }
export interface Dashboard {
  title: string;
  timezone: string;
  weeklyGoal: number;
  now: string;
  live: { since: string } | null;
  sync: { state: string | null; last_ok: string | null; next_at: string | null };
  sessions: RawSession[];
}
export interface Session { start: Date; end: Date | null; minutes: number | null; studio?: string; day: string }

const DAY = 86_400_000;
export const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
export const WEEKDAYS_LONG = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
export const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export const parse = (s: string) => new Date(s.endsWith('Z') ? s : s + 'Z');
export const dayKey = (d: Date) => d.toISOString().slice(0, 10);
export const startOfDay = (d: Date) => new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()));
export const weekday = (d: Date) => (d.getUTCDay() + 6) % 7; // Mon = 0
export const startOfWeek = (d: Date) => new Date(startOfDay(d).getTime() - weekday(d) * DAY);
export const addDays = (d: Date, n: number) => new Date(d.getTime() + n * DAY);
export const hhmm = (d: Date) => d.toISOString().slice(11, 16);
export const fmtDate = (d: Date) => `${WEEKDAYS[weekday(d)]} ${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`;
export const fmtDateY = (d: Date) => `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;

export function fmtDuration(min: number): string {
  if (!isFinite(min) || min <= 0) return '0m';
  const h = Math.floor(min / 60), m = Math.round(min % 60);
  return h ? (m ? `${h}h ${m}m` : `${h}h`) : `${m}m`;
}

export function toSessions(raw: RawSession[]): Session[] {
  return raw
    .map((r) => {
      const start = parse(r.start);
      return { start, end: r.end ? parse(r.end) : null, minutes: r.minutes, studio: r.studio, day: dayKey(start) };
    })
    .sort((a, b) => a.start.getTime() - b.start.getTime());
}

export type Range = '30d' | '90d' | '1y' | 'all';
export const RANGES: { id: Range; label: string; days: number | null }[] = [
  { id: '30d', label: '30 days', days: 30 },
  { id: '90d', label: '90 days', days: 90 },
  { id: '1y', label: '12 months', days: 365 },
  { id: 'all', label: 'All time', days: null },
];

export function inRange(sessions: Session[], range: Range, now: Date): Session[] {
  const days = RANGES.find((r) => r.id === range)!.days;
  if (days === null) return sessions;
  const from = addDays(startOfDay(now), -days + 1).getTime();
  return sessions.filter((s) => s.start.getTime() >= from);
}

/** Visits per week, Monday-based, oldest first, current week last. */
export function weeklyCounts(sessions: Session[], now: Date, weeks: number) {
  const thisWeek = startOfWeek(now);
  const buckets = Array.from({ length: weeks }, (_, i) => ({
    week: addDays(thisWeek, -(weeks - 1 - i) * 7),
    visits: 0,
    minutes: 0,
  }));
  const first = buckets[0].week.getTime();
  for (const s of sessions) {
    const t = startOfWeek(s.start).getTime();
    if (t < first) continue;
    const b = buckets[Math.round((t - first) / (7 * DAY))];
    if (b) { b.visits++; b.minutes += s.minutes ?? 0; }
  }
  return buckets;
}

export function streaks(sessions: Session[], now: Date, goal: number) {
  if (!sessions.length) return { current: 0, best: 0, currentIncludesThisWeek: false };
  const weeks = Math.ceil((startOfWeek(now).getTime() - startOfWeek(sessions[0].start).getTime()) / (7 * DAY)) + 1;
  const counts = weeklyCounts(sessions, now, weeks).map((w) => w.visits);
  let best = 0, run = 0;
  for (const c of counts) { run = c >= goal ? run + 1 : 0; best = Math.max(best, run); }
  // The running week only counts once the goal is reached; until then it doesn't break the streak.
  const thisWeekMet = counts[counts.length - 1] >= goal;
  let current = 0;
  for (let i = counts.length - (thisWeekMet ? 1 : 2); i >= 0 && counts[i] >= goal; i--) current++;
  return { current, best, currentIncludesThisWeek: thisWeekMet };
}

export function summary(sessions: Session[], now: Date, range: Range) {
  const timed = sessions.filter((s) => s.minutes !== null && s.minutes > 0) as (Session & { minutes: number })[];
  const totalMin = timed.reduce((a, s) => a + s.minutes, 0);
  const days = RANGES.find((r) => r.id === range)!.days;
  const spanDays = days ?? (sessions.length ? (now.getTime() - startOfDay(sessions[0].start).getTime()) / DAY + 1 : 0);
  const longest = timed.reduce<(typeof timed)[number] | null>((a, s) => (!a || s.minutes > a.minutes ? s : a), null);
  const minuteOfDay = (d: Date) => d.getUTCHours() * 60 + d.getUTCMinutes();
  const earliest = sessions.reduce<Session | null>((a, s) => (!a || minuteOfDay(s.start) < minuteOfDay(a.start) ? s : a), null);
  const latest = timed.reduce<Session | null>((a, s) => (!a || minuteOfDay(s.end!) > minuteOfDay(a.end!) ? s : a), null);

  const byWeekday = Array(7).fill(0);
  const byHour = Array(24).fill(0);
  for (const s of sessions) { byWeekday[weekday(s.start)]++; byHour[s.start.getUTCHours()]++; }
  const favDay = byWeekday.indexOf(Math.max(...byWeekday));
  const favHour = byHour.indexOf(Math.max(...byHour));

  return {
    visits: sessions.length,
    totalMin,
    avgMin: timed.length ? totalMin / timed.length : 0,
    perWeek: spanDays ? sessions.length / (spanDays / 7) : 0,
    activeDays: new Set(sessions.map((s) => s.day)).size,
    longest,
    earliest,
    latest,
    favDay: sessions.length ? WEEKDAYS_LONG[favDay] : '–',
    favHour: sessions.length ? favHour : null,
  };
}

/** Compare month-to-date against the same days of last month. */
export function monthToDate(sessions: Session[], now: Date) {
  const y = now.getUTCFullYear(), m = now.getUTCMonth(), d = now.getUTCDate();
  const thisStart = Date.UTC(y, m, 1);
  const lastStart = Date.UTC(y, m - 1, 1);
  const lastCut = Date.UTC(y, m - 1, Math.min(d, new Date(Date.UTC(y, m, 0)).getUTCDate()) + 1);
  let cur = 0, prev = 0;
  for (const s of sessions) {
    const t = s.start.getTime();
    if (t >= thisStart) cur++;
    else if (t >= lastStart && t < lastCut) prev++;
  }
  return { cur, prev, label: MONTHS[m] };
}

/** Minutes per day for the last `weeks` weeks, as columns of 7 (Mon..Sun). */
export function calendar(sessions: Session[], now: Date, weeks = 53) {
  const perDay = new Map<string, { minutes: number; visits: number }>();
  for (const s of sessions) {
    const e = perDay.get(s.day) ?? { minutes: 0, visits: 0 };
    e.minutes += s.minutes ?? 45; // unknown duration still shows as a visit
    e.visits++;
    perDay.set(s.day, e);
  }
  const first = addDays(startOfWeek(now), -(weeks - 1) * 7);
  const today = startOfDay(now).getTime();
  const cols = Array.from({ length: weeks }, (_, w) =>
    Array.from({ length: 7 }, (_, d) => {
      const date = addDays(first, w * 7 + d);
      const e = perDay.get(dayKey(date));
      return { date, future: date.getTime() > today, minutes: e?.minutes ?? 0, visits: e?.visits ?? 0 };
    }),
  );
  return cols;
}

/** Visit counts by weekday (rows) and hour (cols). */
export function punchCard(sessions: Session[]) {
  const grid = Array.from({ length: 7 }, () => Array(24).fill(0) as number[]);
  for (const s of sessions) grid[weekday(s.start)][s.start.getUTCHours()]++;
  return grid;
}

export function monthly(sessions: Session[], now: Date, months = 12) {
  const out = Array.from({ length: months }, (_, i) => {
    const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() - (months - 1 - i), 1));
    return { month: d, visits: 0, minutes: 0 };
  });
  for (const s of sessions) {
    const i = out.findIndex((o) => o.month.getUTCFullYear() === s.start.getUTCFullYear() && o.month.getUTCMonth() === s.start.getUTCMonth());
    if (i >= 0) { out[i].visits++; out[i].minutes += s.minutes ?? 0; }
  }
  return out;
}

export function durationHistogram(sessions: Session[], binMin = 15, maxMin = 180) {
  const bins = Array.from({ length: maxMin / binMin + 1 }, (_, i) => ({ from: i * binMin, count: 0 }));
  for (const s of sessions) {
    if (!s.minutes || s.minutes <= 0) continue;
    bins[Math.min(Math.floor(s.minutes / binMin), bins.length - 1)].count++;
  }
  return bins;
}

export interface Shame { level: number; label: string; emoji: string; blurb: string }
export function shame(daysSince: number | null): Shame {
  if (daysSince === null) return { level: 4, label: 'No data', emoji: '🫥', blurb: 'Has he ever been to a gym?' };
  if (daysSince <= 1) return { level: 0, label: 'On fire', emoji: '🔥', blurb: 'Nothing to see here. Annoyingly consistent.' };
  if (daysSince <= 3) return { level: 1, label: 'Respectable', emoji: '💪', blurb: 'Rest day. Allegedly.' };
  if (daysSince <= 6) return { level: 2, label: 'Getting soft', emoji: '🥐', blurb: 'The croissants are winning.' };
  if (daysSince <= 13) return { level: 3, label: 'Wall of Shame', emoji: '🛋️', blurb: 'The couch has a permanent dent now.' };
  return { level: 4, label: 'Hall of Shame', emoji: '🪦', blurb: 'Membership fee: donated to Fitness First.' };
}

export function daysBetween(a: Date, b: Date) {
  return Math.round((startOfDay(b).getTime() - startOfDay(a).getTime()) / DAY);
}

/** Longest stretch without a visit, ending at the next visit or (if still running) today. */
export function longestGap(sessions: Session[], now: Date) {
  let best: { days: number; from: Date; to: Date; ongoing: boolean } | null = null;
  for (let i = 1; i <= sessions.length; i++) {
    if (!sessions[i - 1]) continue;
    const from = sessions[i - 1].start;
    const to = sessions[i]?.start ?? now;
    const days = daysBetween(from, to) - 1; // full days without a check-in in between
    if (days > 0 && (!best || days > best.days)) best = { days, from, to, ongoing: !sessions[i] };
  }
  return best;
}

export function bestWeek(sessions: Session[]) {
  const counts = new Map<number, number>();
  for (const s of sessions) {
    const w = startOfWeek(s.start).getTime();
    counts.set(w, (counts.get(w) ?? 0) + 1);
  }
  let best: { week: Date; visits: number } | null = null;
  for (const [w, n] of counts) if (!best || n > best.visits || (n === best.visits && w > best.week.getTime())) best = { week: new Date(w), visits: n };
  return best;
}

export function weekdayCounts(sessions: Session[]) {
  const out = Array(7).fill(0) as number[];
  for (const s of sessions) out[weekday(s.start)]++;
  return out;
}
