<script lang="ts">
  import { tip } from './tip.svelte';
  let el: HTMLDivElement | undefined = $state();
  let w = $state(0);
  const left = $derived(Math.max(8, Math.min(tip.x - w / 2, (typeof window !== 'undefined' ? window.innerWidth : 1000) - w - 8)));
</script>

{#if tip.show}
  <div class="tip" bind:this={el} bind:clientWidth={w} style:left="{left}px" style:top="{tip.y - 12}px" role="tooltip">
    <strong>{tip.title}</strong>
    {#each tip.lines as line}<span>{line}</span>{/each}
  </div>
{/if}

<style>
  .tip {
    position: fixed;
    transform: translateY(-100%);
    z-index: 50;
    pointer-events: none;
    background: var(--text);
    color: var(--bg);
    border-radius: 10px;
    padding: 7px 10px;
    font-size: 0.8rem;
    line-height: 1.35;
    display: flex;
    flex-direction: column;
    white-space: nowrap;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
  }
  strong {
    font-weight: 600;
  }
  span {
    opacity: 0.8;
  }
</style>
