import type { ReactNode } from "react";

interface Props {
  icon: ReactNode;
  label: string;
  value: string;
  note: string;
  tone?: "teal" | "blue" | "amber" | "red";
}

export function MetricCard({ icon, label, value, note, tone = "teal" }: Props) {
  return (
    <div className={`c1-stat c1-stat--${tone}`}>
      <div className="c1-stat__icon">{icon}</div>
      <div className="c1-stat__body">
        <span className="c1-stat__label">{label}</span>
        <strong className="c1-stat__value">{value}</strong>
        <span className="c1-stat__note">{note}</span>
      </div>
    </div>
  );
}
