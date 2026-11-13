export const tip = $state({ show: false, x: 0, y: 0, title: '', lines: [] as string[] });

export function showTip(e: PointerEvent | FocusEvent, title: string, lines: string[] = []) {
  let x: number, y: number;
  if ('clientX' in e) {
    x = e.clientX;
    y = e.clientY;
  } else {
    const r = (e.target as Element).getBoundingClientRect();
    x = r.left + r.width / 2;
    y = r.top;
  }
  Object.assign(tip, { show: true, x, y, title, lines });
}

export function hideTip() {
  tip.show = false;
}

/** Spread onto an SVG element: hover + keyboard focus both show the tooltip. */
export function tipProps(title: string, lines: string[] = []) {
  return {
    tabindex: 0,
    role: 'img',
    'aria-label': [title, ...lines].join(', '),
    onpointerenter: (e: PointerEvent) => showTip(e, title, lines),
    onpointermove: (e: PointerEvent) => showTip(e, title, lines),
    onpointerleave: hideTip,
    onfocus: (e: FocusEvent) => showTip(e, title, lines),
    onblur: hideTip,
  };
}

/** Rect with rounded top corners, anchored to the baseline. */
export function barPath(x: number, y: number, w: number, h: number, r = 4) {
  if (h <= 0) return '';
  r = Math.min(r, w / 2, h);
  return `M${x},${y + h}V${y + r}Q${x},${y} ${x + r},${y}H${x + w - r}Q${x + w},${y} ${x + w},${y + r}V${y + h}Z`;
}
