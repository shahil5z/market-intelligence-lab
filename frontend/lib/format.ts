export const fmtNumber = (v: number | null | undefined, digits = 0) =>
  v === null || v === undefined || Number.isNaN(v)
    ? "n/a"
    : v.toLocaleString("en-GB", { minimumFractionDigits: digits, maximumFractionDigits: digits });

export const fmtGBP = (v: number | null | undefined, digits = 0) => (v === null || v === undefined ? "n/a" : `£${fmtNumber(v, digits)}`);

export const fmtPct = (v: number | null | undefined, digits = 1, signed = false) =>
  v === null || v === undefined ? "n/a" : `${signed && v > 0 ? "+" : ""}${fmtNumber(v, digits)}%`;

export const fmtP = (p: number) => (p < 0.0001 ? "< 0.0001" : p.toFixed(4));

export const compact = (v: number) => new Intl.NumberFormat("en-GB", { notation: "compact", maximumFractionDigits: 1 }).format(v);

// Neutral, colour-blind-friendly chart palette (no brand colours).
export const COLORS = ["#0f766e", "#475569", "#7c3aed", "#0891b2", "#65a30d", "#c2410c", "#be185d", "#a16207"];
