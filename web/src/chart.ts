/** Series colours for exported figures. They match the theme's graph colours in light mode. */
export const FIGURE_COLORS = ["#136b56", "#c2410c", "#6d4fc2", "#a16207", "#1d6fa5", "#be185d"];

export function figureColor(index: number): string {
  return FIGURE_COLORS[((index % FIGURE_COLORS.length) + FIGURE_COLORS.length) % FIGURE_COLORS.length] ?? "#136b56";
}

/** Round axis ticks (steps of 1, 2, 2.5 or 5 × 10^k) that cover [min, max]. Counts step by whole numbers. */
export function niceTicks(min: number, max: number, target = 5, integer = false): number[] {
  if (!Number.isFinite(min) || !Number.isFinite(max)) return [0, 1];
  if (max <= min) max = min + 1;
  const raw = (max - min) / Math.max(1, target);
  const power = 10 ** Math.floor(Math.log10(raw));
  const factors = integer ? [1, 2, 5, 10] : [1, 2, 2.5, 5, 10];
  const nice = (factors.find((factor) => factor * power >= raw) ?? 10) * power;
  const step = integer ? Math.max(1, Math.round(nice)) : nice;
  const start = Math.floor(min / step + 1e-9) * step;
  const ticks: number[] = [];
  for (let value = start; value < max + step - 1e-9; value += step) ticks.push(Number(value.toPrecision(12)));
  return ticks;
}

/** Whole-number ticks for ranks, which start at 1. */
export function rankTicks(min: number, max: number): number[] {
  const ticks = niceTicks(min, max).map(Math.round).filter((tick) => tick >= Math.ceil(min) && tick <= Math.floor(max));
  return [...new Set(ticks.length ? ticks : [Math.round(min)])];
}
