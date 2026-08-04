import { useCallback, useEffect, useMemo, useState } from "react";

const tabs = [
  { id: "snapshot", label: "Snapshot" },
  { id: "analyze", label: "Analyze" },
];

const API_BASE = (process.env.REACT_APP_API_URL || "").replace(/\/$/, "");
const apiUrl = (path) => `${API_BASE}${path}`;

const number = (value, digits = 2) => {
  if (value === null || value === undefined || value === "") return "--";
  const parsed = Number(value);
  return Number.isFinite(parsed)
    ? parsed.toLocaleString(undefined, { maximumFractionDigits: digits })
    : "--";
};

const signedPercent = (value) => {
  if (value === null || value === undefined || value === "") return "--";
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "--";
  return `${parsed >= 0 ? "+" : ""}${parsed.toFixed(2)}%`;
};

const changeTone = (value) => {
  if (value === null || value === undefined || value === "") return "neutral";
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "neutral";
  return parsed >= 0 ? "positive" : "negative";
};

function useJson(url, options = {}) {
  const [state, setState] = useState({ loading: true, data: null, error: "" });

  const reload = useCallback(async () => {
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 30000);
    setState({ loading: true, data: null, error: "" });
    try {
      const response = await fetch(apiUrl(url), { ...options, signal: controller.signal });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`);
      setState({ loading: false, data: body, error: "" });
      return body;
    } catch (error) {
      setState({ loading: false, data: null, error: error.name === "AbortError" ? "The request timed out." : error.message });
      return null;
    } finally {
      window.clearTimeout(timeout);
    }
  }, [url]);

  return { ...state, reload };
}

function Status({ children, tone = "" }) {
  return <p className={`status ${tone}`}>{children}</p>;
}

function QuoteRow({ item, onAnalyze }) {
  return (
    <button className="quote-row" onClick={() => onAnalyze(item.ticker)} type="button">
      <span>
        <strong>{item.ticker}</strong>
        <small>{item.company_name || item.signal || "Market data"}</small>
      </span>
      <span className="quote-price">${number(item.current_price ?? item.price)}</span>
      <span className={changeTone(item.change_pct)}>
        {signedPercent(item.change_pct)}
      </span>
    </button>
  );
}

function Snapshot({ onAnalyze }) {
  const snapshot = useJson("/api/snapshot");
  useEffect(() => {
    snapshot.reload();
  }, [snapshot.reload]);

  if (snapshot.loading) return <div className="loading-panel"><span className="spinner" />Loading market snapshot...</div>;
  if (snapshot.error) return <div className="error-panel"><strong>Market data unavailable</strong><span>{snapshot.error}</span><button onClick={snapshot.reload} type="button">Retry</button></div>;

  const data = snapshot.data || {};
  const sentiment = data.market_sentiment || {};
  const stale = data.data_mode === "fallback";
  const incomplete = data.data_status !== "live";
  return (
    <section className="stack">
      <div className={`source-banner ${stale || incomplete ? "warning" : ""}`}>
        {stale ? "Configured fallback quotes are shown; reconnect for live data." : data.data_status === "unavailable" ? "Market providers are unavailable. No watchlist calls are shown." : incomplete ? "Some market providers are unavailable; these lists may be incomplete." : "Provider-sourced quotes. Leaders and laggards are one-day watchlists, not trade calls."}
      </div>
      <div className="market-grid">
        {(data.market_indexes || []).map((index) => (
          <a className="market-tile" href={index.url} key={index.symbol} rel="noreferrer" target="_blank">
            <span>{index.name}</span><strong>{number(index.price, 0)}</strong><em className={changeTone(index.change_pct)}>{signedPercent(index.change_pct)}</em>
          </a>
        ))}
      </div>
      <div className="metric-strip">
        <div><span>VIX</span><strong>{number(sentiment.vix)}</strong></div>
        <div><span>Fear &amp; Greed</span><strong>{number(sentiment.fear_greed_index, 0)}</strong></div>
        <div><span>10Y Treasury</span><strong>{number(sentiment.treasury_10y)}%</strong></div>
        <div><span>S&amp;P 500 (1M)</span><strong>{signedPercent(sentiment.sp500_monthly_change)}</strong></div>
      </div>
      <div className="two-column">
        <ListPanel title="Market leaders" items={data.leaders || data.strong_buys} onAnalyze={onAnalyze} />
        <ListPanel title="Market laggards" items={data.laggards || data.shorts} onAnalyze={onAnalyze} />
      </div>
      <div className="two-column">
        <ListPanel title="Top gainers" items={data.gainers} onAnalyze={onAnalyze} />
        <ListPanel title="Top losers" items={data.losers} onAnalyze={onAnalyze} />
      </div>
    </section>
  );
}

function ListPanel({ title, items = [], onAnalyze }) {
  return (
    <article className="panel">
      <div className="panel-heading"><h2>{title}</h2><span>{items.length || 0} symbols</span></div>
      {items.length ? items.slice(0, 6).map((item) => <QuoteRow item={item} key={item.ticker} onAnalyze={onAnalyze} />) : <Status>No provider data for this list.</Status>}
    </article>
  );
}

function Analysis({ initialTicker }) {
  const [ticker, setTicker] = useState(initialTicker || "AAPL");
  const [result, setResult] = useState(null);
  const [state, setState] = useState({ loading: false, error: "" });
  useEffect(() => {
    if (initialTicker) setTicker(initialTicker);
  }, [initialTicker]);

  const analyze = async (event) => {
    event?.preventDefault();
    setState({ loading: true, error: "" });
    setResult(null);
    try {
      const response = await fetch(apiUrl("/api/analyze"), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ticker }) });
      const data = await response.json();
      if (!response.ok || data.error) throw new Error(data.error || "Analysis failed");
      setResult(data);
    } catch (error) {
      setState({ loading: false, error: error.message });
      return;
    }
    setState({ loading: false, error: "" });
  };

  const indicatorEntries = useMemo(() => Object.entries(result?.individual_scores || {}), [result]);
  return (
    <section className="stack">
      <form className="search-form" onSubmit={analyze}>
        <label htmlFor="ticker">Ticker or index</label>
        <div><input id="ticker" maxLength="16" onChange={(event) => setTicker(event.target.value.toUpperCase())} pattern="[A-Z0-9.^=\-_.]+" value={ticker} /><button disabled={state.loading} type="submit">{state.loading ? "Analyzing..." : "Analyze"}</button></div>
      </form>
      {state.error && <div className="error-panel"><strong>Analysis unavailable</strong><span>{state.error}</span></div>}
      {result && <article className="analysis">
        <div className="analysis-heading"><div><span className="eyebrow">{result.ticker}</span><h2>{result.company_name}</h2><p>{result.sector} · {result.industry}</p></div><div className="score"><strong>{result.score}</strong><span>{result.recommendation}</span></div></div>
        <div className="source-banner">Source: {result.data_source || "provider"} · Last bar: {result.data_as_of || "unavailable"}</div>
        <div className="metric-strip compact"><div><span>Price</span><strong>${number(result.current_price)}</strong></div><div><span>Technical</span><strong>{number(result.technical_score, 1)}</strong></div><div><span>Fundamental</span><strong>{number(result.fundamental_score, 1)}</strong></div><div><span>Confidence</span><strong>{result.confidence || "--"}</strong></div></div>
        <div className="indicator-grid">{indicatorEntries.map(([name, value]) => <div className="indicator" key={name}><span>{name.replaceAll("_", " ")}</span><strong>{number(value, 1)}</strong><div><i style={{ width: `${Math.max(0, Math.min(100, Number(value) || 0))}%` }} /></div></div>)}</div>
      </article>}
    </section>
  );
}

export default function App() {
  const params = new URLSearchParams(window.location.search);
  const [active, setActive] = useState(params.get("section") === "analyze" ? "analyze" : "snapshot");
  const [ticker, setTicker] = useState(params.get("ticker") || "");
  const changeTab = (tab) => {
    setActive(tab);
    const next = new URL(window.location.href);
    next.searchParams.set("section", tab);
    window.history.replaceState({}, "", next);
  };
  const openAnalyze = (symbol) => {
    setTicker(symbol);
    changeTab("analyze");
    const next = new URL(window.location.href);
    next.searchParams.set("ticker", symbol);
    window.history.replaceState({}, "", next);
  };
  return (
    <main className="app-shell">
      <header className="app-header"><div><p className="eyebrow">StockPulse</p><h1>Market intelligence, with its limits visible.</h1><p className="lede">Provider-sourced analysis for research and paper trading. Every watchlist is labeled by what the data actually supports.</p></div><div className="header-mark">SP</div></header>
      <nav className="tabs" aria-label="Primary navigation">{tabs.map((tab) => <button className={active === tab.id ? "active" : ""} key={tab.id} onClick={() => changeTab(tab.id)} type="button">{tab.label}</button>)}</nav>
      {active === "snapshot" ? <Snapshot onAnalyze={openAnalyze} /> : <Analysis initialTicker={ticker} />}
      <footer>Educational research tool. Not financial advice. Market data may be delayed.</footer>
    </main>
  );
}

export { changeTone, number, signedPercent };
