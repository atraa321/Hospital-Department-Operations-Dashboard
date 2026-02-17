interface MetricCardProps {
  label: string;
  value: string;
  trend: string;
  tone?: 'default' | 'alert' | 'good';
}

export function MetricCard({ label, value, trend, tone = 'default' }: MetricCardProps) {
  return (
    <article className={`metric-card metric-card--${tone}`}>
      <p className="metric-label">{label}</p>
      <h3 className="metric-value">{value}</h3>
      <p className="metric-trend">{trend}</p>
    </article>
  );
}

