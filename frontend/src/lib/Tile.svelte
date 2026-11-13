<script lang="ts">
  interface Props { label: string; value: string; unit?: string; note?: string; delta?: number | null }
  let { label, value, unit = '', note = '', delta = null }: Props = $props();
</script>

<div class="tile card">
  <span class="label">{label}</span>
  <span class="value num">{value}{#if unit}<small>{unit}</small>{/if}</span>
  {#if delta !== null}
    <span class="note" class:up={delta > 0} class:down={delta < 0}>
      <span aria-hidden="true">{delta > 0 ? '▲' : delta < 0 ? '▼' : '■'}</span>
      {note}
    </span>
  {:else if note}
    <span class="note">{note}</span>
  {/if}
</div>

<style>
  .tile {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 16px 18px;
  }
  .label {
    color: var(--text-2);
    font-size: 0.82rem;
  }
  .value {
    font-size: 1.9rem;
    font-weight: 700;
    line-height: 1.1;
  }
  .value small {
    font-size: 0.5em;
    margin-left: 3px;
    color: var(--muted);
    font-weight: 500;
  }
  .note {
    color: var(--muted);
    font-size: 0.8rem;
  }
  .note span {
    font-size: 0.7em;
    margin-right: 2px;
  }
  .up span {
    color: var(--good);
  }
  .down span {
    color: var(--critical);
  }
</style>
