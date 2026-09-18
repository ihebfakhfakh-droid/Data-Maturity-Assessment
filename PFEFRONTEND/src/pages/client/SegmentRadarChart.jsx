import {
  Bar,
  BarChart,
  CartesianGrid,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

function RadarTooltip({ active, payload, max }) {
  if (!active || !payload?.length) return null
  const row = payload[0]?.payload
  if (!row) return null
  return (
    <div className="radarTooltip">
      <div className="radarTooltipTitle">{row.fullLabel}</div>
      <div className="radarTooltipScore">
        Score: <strong>{row.score}</strong> / {max}
      </div>
    </div>
  )
}

function BarTooltip({ active, payload, max }) {
  if (!active || !payload?.length) return null
  const row = payload[0]?.payload
  if (!row) return null
  return (
    <div className="radarTooltip">
      <div className="radarTooltipTitle">{row.fullLabel}</div>
      <div className="radarTooltipScore">
        Score: <strong>{row.score}</strong> / {max}
      </div>
    </div>
  )
}

/**
 * Spider chart for question scores inside the active domain.
 * `points` uses items like: { key, shortLabel, hint, score }
 */
export function SegmentRadarChart({ title, points }) {
  const max = 5
  const data = (points ?? []).map((p) => ({
    axis: p.shortLabel,
    score: p.score == null || !Number.isFinite(Number(p.score)) ? 0 : Number(p.score),
    fullLabel: [p.label, p.hint].filter(Boolean).join(' · '),
  }))

  if (!data.length) return null
  const useBarChart = data.length <= 2

  return (
    <section className="radarSection" aria-label={useBarChart ? 'Domain question bar chart' : 'Domain question radar'}>
      <div className="radarSectionHead">
        <h2 className="radarHeading">{title || 'Domain questions'}</h2>
      </div>

      <div className="radarChartWrap radarChartWrapSm">
        {useBarChart ? (
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={data} margin={{ top: 18, right: 22, left: 0, bottom: 18 }}>
              <CartesianGrid stroke="#cbd5e1" strokeDasharray="4 4" vertical={false} />
              <XAxis
                dataKey="axis"
                tick={{ fill: '#475569', fontSize: 11 }}
                tickLine={false}
                axisLine={{ stroke: '#cbd5e1' }}
              />
              <YAxis
                domain={[0, max]}
                ticks={[0, 1, 2, 3, 4, 5]}
                tick={{ fill: '#64748b', fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                width={34}
              />
              <Tooltip content={(p) => <BarTooltip {...p} max={max} />} />
              <Bar
                name="Score"
                dataKey="score"
                fill="var(--accent-lagoon)"
                radius={[8, 8, 4, 4]}
                maxBarSize={72}
                isAnimationActive
              />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <ResponsiveContainer width="100%" height={380}>
            <RadarChart cx="50%" cy="52%" outerRadius="72%" data={data}>
              <PolarGrid stroke="#cbd5e1" strokeDasharray="4 4" />
              <PolarAngleAxis
                dataKey="axis"
                tick={{ fill: '#475569', fontSize: data.length > 16 ? 8 : 9 }}
                tickLine={false}
              />
              <PolarRadiusAxis
                angle={90}
                domain={[0, max]}
                ticks={[0, 1, 2, 3, 4, 5]}
                tick={{ fill: '#64748b', fontSize: 10 }}
                stroke="#94a3b8"
                axisLine={false}
              />
              <Tooltip content={(p) => <RadarTooltip {...p} max={max} />} />
              <Radar
                name="Score"
                dataKey="score"
                stroke="var(--accent-lagoon)"
                strokeWidth={2}
                fill="color-mix(in srgb, var(--accent-lagoon) 55%, transparent)"
                fillOpacity={0.35}
                dot={{ r: 2.5, fill: 'var(--accent-lagoon)', strokeWidth: 0 }}
                isAnimationActive
              />
            </RadarChart>
          </ResponsiveContainer>
        )}
      </div>
    </section>
  )
}

