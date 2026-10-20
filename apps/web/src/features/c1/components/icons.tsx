// small inline icons, no icon library needed
const base = { width: 20, height: 20, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.8, strokeLinecap: "round" as const, strokeLinejoin: "round" as const };

export const ShieldIcon = () => (
  <svg {...base}><path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6l7-3z" /><path d="M9 12l2 2 4-4" /></svg>
);
export const PulseIcon = () => (
  <svg {...base}><path d="M3 12h4l2-6 4 12 2-6h6" /></svg>
);
export const ChartIcon = () => (
  <svg {...base}><path d="M4 20V4M4 20h16" /><path d="M8 15l3-4 3 2 5-6" /></svg>
);
export const LayersIcon = () => (
  <svg {...base}><path d="M12 3l9 5-9 5-9-5 9-5z" /><path d="M3 13l9 5 9-5" /></svg>
);
export const WarnIcon = () => (
  <svg {...base}><path d="M12 4l9 16H3L12 4z" /><path d="M12 10v4M12 17.5v.01" /></svg>
);
