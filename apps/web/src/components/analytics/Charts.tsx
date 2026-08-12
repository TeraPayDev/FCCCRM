import type { ReactNode } from "react";
import "./charts.css";

type Point = { label: string; value: number | null };

function extent(points: Point[]) {
  const values = points.map((p) => p.value).filter((v): v is number => Number.isFinite(v));
  if (!values.length) return { min: 0, max: 1 };
  const min = Math.min(...values);
  const max = Math.max(...values);
  return { min, max: min === max ? max + 1 : max };
}

export function LineChart({
  title,
  subtitle,
  points,
  unit = "",
}: {
  title: string;
  subtitle?: string;
  points: Point[];
  unit?: string;
}) {
  const clean = points.slice(-32);
  const { min, max } = extent(clean);
  const w = 720;
  const h = 230;
  const pad = 28;
  const coords = clean
    .map((point, index) => {
      if (point.value === null || !Number.isFinite(point.value)) return null;
      const x = pad + (index * (w - pad * 2)) / Math.max(clean.length - 1, 1);
      const y = h - pad - ((point.value - min) / (max - min)) * (h - pad * 2);
      return { x, y, point };
    })
    .filter((v): v is NonNullable<typeof v> => Boolean(v));
  const path = coords
    .map((c, i) => `${i ? "L" : "M"}${c.x.toFixed(1)},${c.y.toFixed(1)}`)
    .join(" ");
  const area = coords.length
    ? `${path} L${coords.at(-1)?.x ?? pad},${h - pad} L${coords[0].x},${h - pad} Z`
    : "";

  return (
    <article className="viz-card">
      <header>
        <div>
          <h3>{title}</h3>
          {subtitle && <p>{subtitle}</p>}
        </div>
        <span className="viz-unit">{unit}</span>
      </header>
      <svg className="line-chart" viewBox={`0 0 ${w} ${h}`} role="img" aria-label={title}>
        {[0.25, 0.5, 0.75].map((f) => (
          <line
            key={f}
            x1={pad}
            x2={w - pad}
            y1={pad + (h - pad * 2) * f}
            y2={pad + (h - pad * 2) * f}
            className="chart-grid"
          />
        ))}
        {area && <path d={area} className="chart-area" />}
        {path && <path d={path} className="chart-line" />}
        {coords.map((c, i) => (
          <circle key={i} cx={c.x} cy={c.y} r="3.2" className="chart-dot">
            <title>{`${c.point.label}: ${c.point.value}${unit}`}</title>
          </circle>
        ))}
        <text x={pad} y={17} className="axis-label">
          {max.toFixed(1)}
          {unit}
        </text>
        <text x={pad} y={h - 7} className="axis-label">
          {min.toFixed(1)}
          {unit}
        </text>
      </svg>
      <div className="chart-axis-foot">
        <span>{clean[0]?.label ?? ""}</span>
        <span>{clean.at(-1)?.label ?? ""}</span>
      </div>
    </article>
  );
}

export function BarChart({
  title,
  subtitle,
  points,
  unit = "",
}: {
  title: string;
  subtitle?: string;
  points: Point[];
  unit?: string;
}) {
  const clean = points.slice(-16);
  const max = Math.max(1, ...clean.map((p) => p.value ?? 0));
  return (
    <article className="viz-card">
      <header>
        <div>
          <h3>{title}</h3>
          {subtitle && <p>{subtitle}</p>}
        </div>
        <span className="viz-unit">{unit}</span>
      </header>
      <div className="bar-chart">
        {clean.map((p, i) => (
          <div
            className="bar-item"
            key={`${p.label}-${i}`}
            title={`${p.label}: ${p.value ?? "No data"}${unit}`}
          >
            <div className="bar-track">
              <div
                className="bar-fill"
                style={{ height: `${Math.max(2, ((p.value ?? 0) / max) * 100)}%` }}
              />
            </div>
            <span>{p.label.slice(-5)}</span>
          </div>
        ))}
      </div>
    </article>
  );
}

export function Donut({
  title,
  value,
  total,
  centerLabel,
  children,
}: {
  title: string;
  value: number;
  total: number;
  centerLabel: string;
  children?: ReactNode;
}) {
  const pct = total ? Math.max(0, Math.min(100, (value / total) * 100)) : 0;
  return (
    <article className="viz-card donut-card">
      <header>
        <div>
          <h3>{title}</h3>
        </div>
      </header>
      <div className="donut-wrap">
        <div
          className="donut"
          style={{ background: `conic-gradient(var(--green) ${pct}%, #e8f0f2 0)` }}
        >
          <div>
            <strong>{Math.round(pct)}%</strong>
            <span>{centerLabel}</span>
          </div>
        </div>
        <div className="donut-copy">{children}</div>
      </div>
    </article>
  );
}

export function MetricTile({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: "default" | "good" | "warn" | "bad";
}) {
  return (
    <article className={`metric-tile ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {hint && <small>{hint}</small>}
    </article>
  );
}

export function ForecastChart({
  title,
  subtitle,
  history,
  forecast,
  unit = "",
}: {
  title: string;
  subtitle?: string;
  history: Point[];
  forecast: Array<Point & { lower?: number | null; upper?: number | null }>;
  unit?: string;
}) {
  const historical = history.slice(-20);
  const combined = [...historical, ...forecast];
  const values = combined.flatMap((p, i) => {
    const f = i >= historical.length ? forecast[i - historical.length] : undefined;
    return [p.value, f?.lower ?? null, f?.upper ?? null].filter(
      (v): v is number => typeof v === "number" && Number.isFinite(v),
    );
  });
  const min = values.length ? Math.min(...values) : 0;
  const rawMax = values.length ? Math.max(...values) : 1;
  const max = rawMax === min ? min + 1 : rawMax;
  const w = 760,
    h = 250,
    pad = 30;
  const x = (index: number) => pad + (index * (w - pad * 2)) / Math.max(combined.length - 1, 1);
  const y = (value: number) => h - pad - ((value - min) / (max - min)) * (h - pad * 2);
  const historyCoords = historical
    .map((p, i) => (p.value == null ? null : { x: x(i), y: y(p.value), p }))
    .filter((v): v is NonNullable<typeof v> => Boolean(v));
  const forecastCoords = forecast
    .map((p, i) => (p.value == null ? null : { x: x(historical.length + i), y: y(p.value), p }))
    .filter((v): v is NonNullable<typeof v> => Boolean(v));
  const join =
    historyCoords.length && forecastCoords.length
      ? [historyCoords.at(-1)!, ...forecastCoords]
      : forecastCoords;
  const historyPath = historyCoords
    .map((c, i) => `${i ? "L" : "M"}${c.x.toFixed(1)},${c.y.toFixed(1)}`)
    .join(" ");
  const forecastPath = join
    .map((c, i) => `${i ? "L" : "M"}${c.x.toFixed(1)},${c.y.toFixed(1)}`)
    .join(" ");
  const upper = forecast
    .map((p, i) => (p.upper == null ? null : { x: x(historical.length + i), y: y(p.upper) }))
    .filter((v): v is NonNullable<typeof v> => Boolean(v));
  const lower = forecast
    .map((p, i) => (p.lower == null ? null : { x: x(historical.length + i), y: y(p.lower) }))
    .filter((v): v is NonNullable<typeof v> => Boolean(v));
  const band =
    upper.length && lower.length
      ? `${upper.map((c, i) => `${i ? "L" : "M"}${c.x.toFixed(1)},${c.y.toFixed(1)}`).join(" ")} ${[
          ...lower,
        ]
          .reverse()
          .map((c) => `L${c.x.toFixed(1)},${c.y.toFixed(1)}`)
          .join(" ")} Z`
      : "";
  const dividerX = forecast.length ? x(Math.max(0, historical.length - 1)) : 0;
  return (
    <article className="viz-card forecast-card">
      <header>
        <div>
          <h3>{title}</h3>
          {subtitle && <p>{subtitle}</p>}
        </div>
        <span className="viz-unit">{unit}</span>
      </header>
      <svg className="line-chart" viewBox={`0 0 ${w} ${h}`} role="img" aria-label={title}>
        {[0.25, 0.5, 0.75].map((f) => (
          <line
            key={f}
            x1={pad}
            x2={w - pad}
            y1={pad + (h - pad * 2) * f}
            y2={pad + (h - pad * 2) * f}
            className="chart-grid"
          />
        ))}
        {band && <path d={band} className="forecast-band" />}
        {historyPath && <path d={historyPath} className="chart-line" />}
        {forecastPath && <path d={forecastPath} className="forecast-line" />}
        {forecast.length > 0 && (
          <line x1={dividerX} x2={dividerX} y1={pad} y2={h - pad} className="forecast-divider" />
        )}
        <text x={Math.min(w - 100, dividerX + 8)} y={pad + 12} className="forecast-label">
          FORECAST
        </text>
        {historyCoords.map((c, i) => (
          <circle key={`h${i}`} cx={c.x} cy={c.y} r="3" className="chart-dot" />
        ))}
        {forecastCoords.map((c, i) => (
          <circle key={`f${i}`} cx={c.x} cy={c.y} r="3.4" className="forecast-dot">
            <title>{`${c.p.label}: ${c.p.value}${unit}`}</title>
          </circle>
        ))}
      </svg>
      <div className="forecast-legend">
        <span>
          <i className="history-key" />
          Observed trend
        </span>
        <span>
          <i className="forecast-key" />
          Engineering forecast
        </span>
        <span>
          <i className="band-key" />
          Residual uncertainty band
        </span>
      </div>
    </article>
  );
}
