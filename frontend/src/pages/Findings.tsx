import { useEffect, useState, useTransition } from "react";
import { FindingCard } from "../components/FindingCard";
import { fetchFindings, triggerScan, type Finding } from "../lib/api";

export function FindingsPage() {
  const [findings, setFindings] = useState<Finding[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pending, startTransition] = useTransition();

  const load = () => {
    setLoading(true);
    setError(null);
    fetchFindings()
      .then((data) => setFindings(data))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const onRescan = () => {
    startTransition(async () => {
      try {
        setError(null);
        await triggerScan();
        const data = await fetchFindings();
        setFindings(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Scan failed");
      }
    });
  };

  const totalSavings = findings.reduce((s, f) => s + (f.estimated_monthly_savings_usd || 0), 0);

  return (
    <div className="page">
      <header className="hero">
        <p className="brand">Quorom</p>
        <h1>Findings</h1>
        <p className="hero__sub">
          Detect + Reason. Read-only view of idle and oversized AWS resources the agent flagged.
        </p>
        <div className="hero__actions">
          <button type="button" className="btn primary" onClick={onRescan} disabled={pending}>
            {pending ? "Scanning..." : "Run scan"}
          </button>
          <button type="button" className="btn ghost" onClick={load} disabled={loading}>
            Refresh
          </button>
          {totalSavings > 0 && (
            <span className="savings-pill">~${totalSavings.toFixed(0)}/mo suggested</span>
          )}
        </div>
      </header>

      {error && <p className="banner error">{error}</p>}
      {loading && <p className="banner muted">Loading findings...</p>}

      {!loading && !error && findings.length === 0 && (
        <p className="banner muted">No findings yet. Run a scan to populate.</p>
      )}

      <section className="findings-grid" aria-label="Findings">
        {findings.map((f) => (
          <FindingCard key={f.id} finding={f} />
        ))}
      </section>
    </div>
  );
}
