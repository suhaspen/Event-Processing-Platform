import React, { useMemo, useState } from "react";

type Json = Record<string, unknown> | Record<string, unknown>[] | null;

const pretty = (value: Json): string =>
  value === null ? "" : JSON.stringify(value, null, 2);

export const Dashboard: React.FC = () => {
  const [mode, setMode] = useState<"auth" | "analytics">("auth");

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [jwt, setJwt] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState<string | null>(null);

  const [ingestResult, setIngestResult] = useState<Json>(null);
  const [health, setHealth] = useState<Json>(null);
  const [systemMetrics, setSystemMetrics] = useState<Json>(null);
  const [eventList, setEventList] = useState<Json>(null);

  const [teamA, setTeamA] = useState("Entity A");
  const [teamB, setTeamB] = useState("Entity B");
  const [teamAElo, setTeamAElo] = useState(1665);
  const [teamBElo, setTeamBElo] = useState(1625);
  const [teamARecentWinPct, setTeamARecentWinPct] = useState(0.8);
  const [teamBRecentWinPct, setTeamBRecentWinPct] = useState(0.6);
  const [teamAPointsPerGame, setTeamAPointsPerGame] = useState(28.4);
  const [teamBPointsPerGame, setTeamBPointsPerGame] = useState(26.1);
  const [teamAPointsAllowedPerGame, setTeamAPointsAllowedPerGame] =
    useState(20.5);
  const [teamBPointsAllowedPerGame, setTeamBPointsAllowedPerGame] =
    useState(22.7);
  const [teamATurnoverDiff, setTeamATurnoverDiff] = useState(6);
  const [teamBTurnoverDiff, setTeamBTurnoverDiff] = useState(2);
  const [teamARestDays, setTeamARestDays] = useState(7);
  const [teamBRestDays, setTeamBRestDays] = useState(6);
  const [isTeamAHome, setIsTeamAHome] = useState(true);
  const [teamAQbStatus, setTeamAQbStatus] = useState(1.0);
  const [teamBQbStatus, setTeamBQbStatus] = useState(1.0);

  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isAuthed = useMemo(() => Boolean(jwt), [jwt]);

  const baseHeaders: HeadersInit = useMemo(
    () => ({
      "Content-Type": "application/json",
      ...(jwt ? { Authorization: `Bearer ${jwt}` } : {}),
      ...(apiKey ? { "X-API-Key": apiKey } : {})
    }),
    [jwt, apiKey]
  );

  const api = async (
    input: RequestInfo,
    init?: RequestInit
  ): Promise<unknown> => {
    const res = await fetch(input, init);
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || res.statusText);
    }
    const contentType = res.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      return res.json();
    }
    return res.text();
  };

  const handleSignup = async () => {
    setLoading(true);
    setError(null);
    setStatus("Creating account…");
    try {
      await api("/api/v1/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      setStatus("Signup successful. You can now log in.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async () => {
    setLoading(true);
    setError(null);
    setStatus("Logging in…");
    try {
      const res = (await api("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      })) as { access_token: string; api_key: string };
      setJwt(res.access_token);
      setApiKey(res.api_key);
      setStatus("Logged in. Analytics ready.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  // Optional manual rotation (rarely needed now that login returns a key)
  const handleCreateApiKey = async () => {
    if (!jwt) {
      setStatus("Log in first to create an API key.");
      return;
    }
    setLoading(true);
    setError(null);
    setStatus("Rotating API key…");
    try {
      const res = (await api("/api/v1/auth/api-key", {
        method: "POST",
        headers: baseHeaders
      })) as { api_key: string };
      setApiKey(res.api_key);
      setStatus("API key rotated and attached to requests.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitEvent = async () => {
    setLoading(true);
    setError(null);
    setStatus("Ingesting structured event…");
    try {
      const payload = {
        entity_a: teamA,
        entity_b: teamB,
        entity_a_elo: teamAElo,
        entity_b_elo: teamBElo,
        entity_a_recent_win_pct: teamARecentWinPct,
        entity_b_recent_win_pct: teamBRecentWinPct,
        entity_a_points_per_game: teamAPointsPerGame,
        entity_b_points_per_game: teamBPointsPerGame,
        entity_a_points_allowed_per_game: teamAPointsAllowedPerGame,
        entity_b_points_allowed_per_game: teamBPointsAllowedPerGame,
        entity_a_turnover_diff: teamATurnoverDiff,
        entity_b_turnover_diff: teamBTurnoverDiff,
        entity_a_rest_days: teamARestDays,
        entity_b_rest_days: teamBRestDays,
        primary_plays_at_home: isTeamAHome,
        entity_a_lead_status: teamAQbStatus,
        entity_b_lead_status: teamBQbStatus
      };

      const res = (await api("/api/v1/events", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(apiKey ? { "X-API-Key": apiKey } : {})
        },
        body: JSON.stringify({
          event_type: "demo.session.metrics",
          source: "dashboard",
          payload
        })
      })) as Json;

      setIngestResult(res);
      setStatus("Event stored.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleFetchHealthAndMetrics = async () => {
    setLoading(true);
    setError(null);
    setStatus("Checking service health…");
    try {
      const [h, m] = (await Promise.all([
        api("/api/v1/health"),
        api("/api/v1/metrics", { headers: baseHeaders })
      ])) as [Json, Json];
      setHealth(h);
      setSystemMetrics(m);
      setStatus("Health and platform metrics loaded.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleFetchRecentEvents = async () => {
    setLoading(true);
    setError(null);
    setStatus("Loading recent events…");
    try {
      const res = (await api("/api/v1/events?limit=10", {
        headers: baseHeaders
      })) as Json;
      setEventList(res);
      setStatus("Recent events loaded.");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span
              style={{
                width: 26,
                height: 26,
                borderRadius: 8,
                background:
                  "conic-gradient(from 160deg, #22c55e, #22c55e, #2dd4bf, #60a5fa, #4f46e5, #22c55e)",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 0 24px rgba(56, 189, 248, 0.9)"
              }}
            >
              <span
                style={{
                  width: 18,
                  height: 18,
                  borderRadius: 6,
                  background: "#020617"
                }}
              />
            </span>
            <div>
              <div style={{ fontSize: "0.95rem", fontWeight: 600 }}>
                Event Processing &amp; Analytics
              </div>
              <div
                style={{
                  fontSize: "0.75rem",
                  color: "#9ca3af"
                }}
              >
                Ingest events, query history, and inspect platform health
              </div>
            </div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <div className="tabs">
            <button
              className={`tab ${mode === "auth" ? "active" : ""}`}
              onClick={() => setMode("auth")}
            >
              Auth & Keys
            </button>
            <button
              className={`tab ${mode === "analytics" ? "active" : ""}`}
              onClick={() => setMode("analytics")}
            >
              Analytics
            </button>
          </div>
          <span className="badge">
            {isAuthed ? "Session: ready for analytics" : "Session: guest"}
          </span>
        </div>
      </header>

      {mode === "auth" ? (
        <main className="app-main">
          <section className="panel">
            <div className="panel-header">
              <div>
                <div className="panel-title">JWT login & signup</div>
                <div className="panel-subtitle">
                  Work with your `/auth/signup` and `/auth/login` endpoints.
                </div>
              </div>
            </div>
            <div className="grid-2">
              <div className="form-field">
                <label className="label">Email</label>
                <input
                  className="input"
                  value={email}
                  type="email"
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                />
              </div>
              <div className="form-field">
                <label className="label">Password</label>
                <input
                  className="input"
                  value={password}
                  type="password"
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>
            </div>
            <div
              style={{
                display: "flex",
                gap: "0.5rem",
                marginTop: "0.75rem"
              }}
            >
              <button
                className="button secondary"
                disabled={loading}
                onClick={handleSignup}
              >
                Create account
              </button>
              <button
                className="button"
                disabled={loading}
                onClick={handleLogin}
              >
                Log in & store JWT
              </button>
            </div>
            <div className="pill-row">
              <span className="pill">
                JWT stored in memory only (no localStorage)
              </span>
              {jwt && <span className="pill">JWT ready for API calls</span>}
            </div>
            <div style={{ marginTop: "0.75rem" }} className="code-block">
              <span style={{ opacity: 0.7 }}>access_token</span>
              <br />
              {jwt ? (
                <span style={{ wordBreak: "break-all" }}>{jwt}</span>
              ) : (
                <span style={{ opacity: 0.5 }}>
                  Log in to see issued token…
                </span>
              )}
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <div className="panel-title">API key & session state</div>
                <div className="panel-subtitle">
                  Hit your `/auth/api-key` route and attach keys to requests.
                </div>
              </div>
              <span className="chip">
                Header: <code>X-API-Key</code>
              </span>
            </div>
            <div className="stack">
              <div className="stack-row">
                <div>
                  <div className="metric">
                    {apiKey ? "Key ready" : "No key yet"}
                  </div>
                  <div className="metric-label">
                    Created via <code>/api/v1/auth/api-key</code>
                  </div>
                </div>
                {apiKey && (
                  <button
                    className="button ghost"
                    disabled={loading || !jwt}
                    onClick={handleCreateApiKey}
                  >
                    Rotate key
                  </button>
                )}
              </div>
              <div className="code-block">
                <span style={{ opacity: 0.7 }}>X-API-Key</span>
                <br />
                {apiKey ? (
                  <span style={{ wordBreak: "break-all" }}>{apiKey}</span>
                ) : (
                  <span style={{ opacity: 0.5 }}>
                    No key yet. Log in and generate one.
                  </span>
                )}
              </div>
              <div className="pill-row">
                <span className="chip">
                  All analytics calls will send your API key.
                </span>
                <span className="chip warn">
                  Make sure your backend route requires a JWT auth dependency.
                </span>
              </div>
            </div>
          </section>
        </main>
      ) : (
        <main className="app-main">
          <section className="panel">
              <div className="panel-header">
              <div>
                <div className="panel-title">Event ingestion playground</div>
                <div className="panel-subtitle">
                  Submit a structured payload as JSON (demo session metrics) and
                  inspect the stored event plus recent history.
                </div>
              </div>
              <span className="badge">
                {apiKey ? "API key attached" : "API key missing"}
              </span>
            </div>

              <div className="stack">
              <div className="stack-row">
                <div>
                  <div className="metric">
                    {ingestResult && typeof ingestResult === "object"
                      ? String(
                          (ingestResult as Record<string, unknown>).id ?? "—"
                        )
                      : "—"}
                  </div>
                  <div className="metric-label">Last event ID</div>
                </div>
                <div>
                  <div className="metric">
                    {ingestResult && typeof ingestResult === "object"
                      ? String(
                          (ingestResult as Record<string, unknown>).event_type ??
                            "—"
                        )
                      : "—"}
                  </div>
                  <div className="metric-label">Event type</div>
                </div>
                <div className="pill-row">
                  <span className="pill">
                    Occurred:{" "}
                    {ingestResult && typeof ingestResult === "object"
                      ? String(
                          (ingestResult as Record<string, unknown>)
                            .occurred_at ?? "—"
                        )
                      : "—"}
                  </span>
                  <span className="pill">
                    Source:{" "}
                    {ingestResult && typeof ingestResult === "object"
                      ? String(
                          (ingestResult as Record<string, unknown>).source ??
                            "—"
                        )
                      : "—"}
                  </span>
                </div>
              </div>

              <div className="grid-2">
                <div className="form-field">
                  <label className="label">Entity A name</label>
                  <input
                    className="input"
                    value={teamA}
                    onChange={(e) => setTeamA(e.target.value)}
                  />
                </div>
                <div className="form-field">
                  <label className="label">Entity B name</label>
                  <input
                    className="input"
                    value={teamB}
                    onChange={(e) => setTeamB(e.target.value)}
                  />
                </div>
                <div className="form-field">
                  <label className="label">Entity A Elo</label>
                  <input
                    className="input"
                    type="number"
                    value={teamAElo}
                    onChange={(e) => setTeamAElo(Number(e.target.value) || 0)}
                  />
                </div>
                <div className="form-field">
                  <label className="label">Entity B Elo</label>
                  <input
                    className="input"
                    type="number"
                    value={teamBElo}
                    onChange={(e) => setTeamBElo(Number(e.target.value) || 0)}
                  />
                </div>
                <div className="form-field">
                  <label className="label">Entity A recent win %</label>
                  <input
                    className="input"
                    type="number"
                    min={0}
                    max={1}
                    step={0.05}
                    value={teamARecentWinPct}
                    onChange={(e) =>
                      setTeamARecentWinPct(Number(e.target.value) || 0)
                    }
                  />
                </div>
                <div className="form-field">
                  <label className="label">Entity B recent win %</label>
                  <input
                    className="input"
                    type="number"
                    min={0}
                    max={1}
                    step={0.05}
                    value={teamBRecentWinPct}
                    onChange={(e) =>
                      setTeamBRecentWinPct(Number(e.target.value) || 0)
                    }
                  />
                </div>
                <div className="form-field">
                  <label className="label">Entity A points per game</label>
                  <input
                    className="input"
                    type="number"
                    step={0.1}
                    value={teamAPointsPerGame}
                    onChange={(e) =>
                      setTeamAPointsPerGame(Number(e.target.value) || 0)
                    }
                  />
                </div>
                <div className="form-field">
                  <label className="label">Entity B points per game</label>
                  <input
                    className="input"
                    type="number"
                    step={0.1}
                    value={teamBPointsPerGame}
                    onChange={(e) =>
                      setTeamBPointsPerGame(Number(e.target.value) || 0)
                    }
                  />
                </div>
                <div className="form-field">
                  <label className="label">
                    Entity A points allowed per game
                  </label>
                  <input
                    className="input"
                    type="number"
                    step={0.1}
                    value={teamAPointsAllowedPerGame}
                    onChange={(e) =>
                      setTeamAPointsAllowedPerGame(
                        Number(e.target.value) || 0
                      )
                    }
                  />
                </div>
                <div className="form-field">
                  <label className="label">
                    Entity B points allowed per game
                  </label>
                  <input
                    className="input"
                    type="number"
                    step={0.1}
                    value={teamBPointsAllowedPerGame}
                    onChange={(e) =>
                      setTeamBPointsAllowedPerGame(
                        Number(e.target.value) || 0
                      )
                    }
                  />
                </div>
                <div className="form-field">
                  <label className="label">Entity A turnover diff</label>
                  <input
                    className="input"
                    type="number"
                    value={teamATurnoverDiff}
                    onChange={(e) =>
                      setTeamATurnoverDiff(Number(e.target.value) || 0)
                    }
                  />
                </div>
                <div className="form-field">
                  <label className="label">Entity B turnover diff</label>
                  <input
                    className="input"
                    type="number"
                    value={teamBTurnoverDiff}
                    onChange={(e) =>
                      setTeamBTurnoverDiff(Number(e.target.value) || 0)
                    }
                  />
                </div>
                <div className="form-field">
                  <label className="label">Entity A rest days</label>
                  <input
                    className="input"
                    type="number"
                    min={0}
                    value={teamARestDays}
                    onChange={(e) =>
                      setTeamARestDays(Number(e.target.value) || 0)
                    }
                  />
                </div>
                <div className="form-field">
                  <label className="label">Entity B rest days</label>
                  <input
                    className="input"
                    type="number"
                    min={0}
                    value={teamBRestDays}
                    onChange={(e) =>
                      setTeamBRestDays(Number(e.target.value) || 0)
                    }
                  />
                </div>
                <div className="form-field">
                  <label className="label">Is Entity A home?</label>
                  <input
                    className="input"
                    type="checkbox"
                    checked={isTeamAHome}
                    onChange={(e) => setIsTeamAHome(e.target.checked)}
                  />
                </div>
                <div className="form-field">
                  <label className="label">Entity A QB status (0–1)</label>
                  <input
                    className="input"
                    type="number"
                    min={0}
                    max={1}
                    step={0.1}
                    value={teamAQbStatus}
                    onChange={(e) =>
                      setTeamAQbStatus(Number(e.target.value) || 0)
                    }
                  />
                </div>
                <div className="form-field">
                  <label className="label">Entity B QB status (0–1)</label>
                  <input
                    className="input"
                    type="number"
                    min={0}
                    max={1}
                    step={0.1}
                    value={teamBQbStatus}
                    onChange={(e) =>
                      setTeamBQbStatus(Number(e.target.value) || 0)
                    }
                  />
                </div>
              </div>

              <div
                style={{
                  display: "flex",
                  gap: "0.5rem",
                  marginTop: "0.6rem"
                }}
              >
                <button
                  className="button secondary"
                  disabled={loading}
                  onClick={handleFetchHealthAndMetrics}
                >
                  Check health &amp; metrics
                </button>
                <button
                  className="button secondary"
                  disabled={loading || !apiKey}
                  onClick={handleFetchRecentEvents}
                >
                  Load recent events
                </button>
                <button
                  className="button"
                  disabled={loading || !apiKey}
                  onClick={handleSubmitEvent}
                >
                  Submit event
                </button>
              </div>
            </div>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <div className="panel-title">Live API inspector</div>
                <div className="panel-subtitle">
                  See raw JSON responses from your FastAPI endpoints.
                </div>
              </div>
            </div>
            <div className="stack">
              {status && (
                <div className="status">
                  <strong>Status</strong>: {status}
                </div>
              )}
              {error && (
                <div className="status" style={{ color: "#fca5a5" }}>
                  <strong>Error</strong>: {error}
                </div>
              )}
              <div className="stack-row">
                <span className="label">Service health (summary)</span>
                <span className="pill">GET /api/v1/health</span>
              </div>
              <div className="card-row">
                <span>
                  Status:{" "}
                  {health && typeof health === "object"
                    ? String(
                        (health as Record<string, unknown>).status ?? "unknown"
                      )
                    : "unknown"}
                </span>
                <span>
                  DB:{" "}
                  {health && typeof health === "object"
                    ? String(
                        (health as Record<string, unknown>)
                          .database_connected ?? "unknown"
                      )
                    : "unknown"}
                </span>
                <span>
                  Redis:{" "}
                  {health && typeof health === "object"
                    ? String(
                        (health as Record<string, unknown>).redis_connected ??
                          "unknown"
                      )
                    : "unknown"}
                </span>
              </div>
              <div className="code-block">{pretty(health)}</div>

              <div className="stack-row">
                <span className="label">Platform metrics</span>
                <span className="pill">GET /api/v1/metrics</span>
              </div>
              <div className="card-row">
                <span>
                  Total events:{" "}
                  {systemMetrics && typeof systemMetrics === "object"
                    ? String(
                        (systemMetrics as Record<string, unknown>)
                          .events_total ?? "unknown"
                      )
                    : "unknown"}
                </span>
                <span>
                  Cache TTL (s):{" "}
                  {systemMetrics && typeof systemMetrics === "object"
                    ? String(
                        (systemMetrics as Record<string, unknown>)
                          .cache_ttl_seconds ?? "unknown"
                      )
                    : "unknown"}
                </span>
                <span>
                  Redis (metrics probe):{" "}
                  {systemMetrics && typeof systemMetrics === "object"
                    ? String(
                        (systemMetrics as Record<string, unknown>)
                          .redis_connected ?? "unknown"
                      )
                    : "unknown"}
                </span>
              </div>
              <div className="code-block">{pretty(systemMetrics)}</div>

              <div className="stack-row">
                <span className="label">Ingest response</span>
                <span className="pill">POST /api/v1/events</span>
              </div>
              <div className="code-block">{pretty(ingestResult)}</div>

              <div className="stack-row">
                <span className="label">Recent events</span>
                <span className="pill">GET /api/v1/events</span>
              </div>
              <div style={{ marginBottom: "0.5rem" }}>
                {eventList &&
                typeof eventList === "object" &&
                Array.isArray(
                  (eventList as Record<string, unknown>).items
                ) &&
                (
                  (eventList as Record<string, unknown>).items as unknown[]
                ).length > 0 &&
                typeof (
                  (eventList as Record<string, unknown>).items as unknown[]
                )[0] === "object" ? (
                  <table className="table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Type</th>
                        <th>Occurred</th>
                        <th>Source</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(
                        (eventList as Record<string, unknown>)
                          .items as Record<string, unknown>[]
                      ).map((ev) => (
                        <tr key={String(ev.id)}>
                          <td>{String(ev.id)}</td>
                          <td>{String(ev.event_type)}</td>
                          <td>{String(ev.occurred_at)}</td>
                          <td>{String(ev.source ?? "—")}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="code-block">{pretty(eventList)}</div>
                )}
              </div>
            </div>
          </section>
        </main>
      )}
    </div>
  );
};

