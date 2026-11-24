import { useEffect, useState } from "react";

interface HealthResponse {
  status: string;
  service: string;
  version: string;
  deployment_profile: string;
  environment: string;
}

export function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    fetch("/api/health")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<HealthResponse>;
      })
      .then((data) => {
        if (active) setHealth(data);
      })
      .catch((err: unknown) => {
        if (active) setError(err instanceof Error ? err.message : "Unable to reach API");
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <main className="container">
      <header className="hero">
        <span className="badge">Phase 1 Foundation</span>
        <h1>LANCAST</h1>
        <p className="subtitle">
          Adaptive Resource &amp; Security Orchestration Framework for Multi-Tenant Campus Assessments
        </p>
      </header>

      <section className="card">
        <h2>Gateway &amp; API Status</h2>
        {health && (
          <dl className="grid">
            <div>
              <dt>Status</dt>
              <dd className="ok">{health.status}</dd>
            </div>
            <div>
              <dt>Profile</dt>
              <dd>{health.deployment_profile}</dd>
            </div>
            <div>
              <dt>Version</dt>
              <dd>{health.version}</dd>
            </div>
            <div>
              <dt>Environment</dt>
              <dd>{health.environment}</dd>
            </div>
          </dl>
        )}
        {error && <p className="err">API unreachable: {error}</p>}
        {!health && !error && <p className="muted">Checking /api/health...</p>}
      </section>
    </main>
  );
}
