import type { Finding } from "../lib/api";

const actionLabels: Record<string, string> = {
  resize_ec2: "Resize EC2",
  stop_idle_ec2: "Stop idle EC2",
  no_action: "No action",
};

function pct(value: unknown): string {
  if (typeof value !== "number") return "n/a";
  return `${value.toFixed(1)}%`;
}

function metricLine(finding: Finding): string {
  const m = finding.metric_summary;
  if (finding.resource_type === "ec2") {
    return `avg CPU ${pct(m.avg_cpu_pct)} · peak ${pct(m.peak_cpu_pct)} · ${m.lookback_days}d`;
  }
  const inv = typeof m.avg_invocations_per_day === "number" ? m.avg_invocations_per_day : "?";
  const dur = typeof m.avg_duration_ms === "number" ? `${m.avg_duration_ms}ms` : "?";
  return `${inv} inv/day · ${dur} avg · ${m.lookback_days}d`;
}

type Props = { finding: Finding };

export function FindingCard({ finding }: Props) {
  const savings = finding.estimated_monthly_savings_usd;
  return (
    <article className={`finding-card severity-${finding.severity}`}>
      <header className="finding-card__header">
        <div>
          <p className="finding-card__eyebrow">
            {finding.resource_type.toUpperCase()} · {finding.flag_type}
          </p>
          <h2>{finding.resource_name}</h2>
          <p className="finding-card__id">{finding.resource_id}</p>
        </div>
        <div className="finding-card__badges">
          <span className={`badge severity`}>{finding.severity}</span>
          <span className="badge conf">
            {Math.round(finding.agent_confidence * 100)}% conf
          </span>
        </div>
      </header>

      <p className="finding-card__metrics">{metricLine(finding)}</p>
      <p className="finding-card__explanation">{finding.explanation}</p>

      <dl className="finding-card__meta">
        <div>
          <dt>Proposed</dt>
          <dd>{actionLabels[finding.proposed_action] ?? finding.proposed_action}</dd>
        </div>
        <div>
          <dt>Est. savings</dt>
          <dd>{savings > 0 ? `$${savings.toFixed(0)}/mo` : "n/a"}</dd>
        </div>
        <div>
          <dt>Blast radius</dt>
          <dd>{finding.blast_radius || "n/a"}</dd>
        </div>
      </dl>
    </article>
  );
}
