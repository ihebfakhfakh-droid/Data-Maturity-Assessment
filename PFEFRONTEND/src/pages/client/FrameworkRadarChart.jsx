import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'

function yBounds(framework) {
  // UI rule: unanswered questions count as 0, so charts always include 0.
  return { min: 0, max: 5 }
}

function yTicks(framework) {
  return [0, 1, 2, 3, 4, 5]
}

function RadarTooltip({ active, payload, framework }) {
  if (!active || !payload?.length) return null
  const row = payload[0]?.payload
  if (!row) return null
  const { max } = yBounds(framework)
  return (
    <div className="radarTooltip">
      <div className="radarTooltipTitle">{row.fullLabel}</div>
      <div className="radarTooltipScore">
        Overall Score: <strong>{row.score}</strong> / {max}
      </div>
    </div>
  )
}

/**
 * Spider / radar chart for all domains in the active framework (NDI or CMMI).
 */
export function FrameworkRadarChart({ framework, rows, summaryValue, summaryBandLabel }) {
  const { min, max } = yBounds(framework)
  const ticks = yTicks(framework)

  const title = framework === 'ndi' ? 'NDI results' : 'CMMI DMM results'
  const palette = framework === 'ndi'
    ? { stroke: 'var(--accent-lagoon)', fill: 'color-mix(in srgb, var(--accent-lagoon) 55%, transparent)', dot: 'var(--accent-lagoon)' }
    : { stroke: 'var(--accent-violet)', fill: 'color-mix(in srgb, var(--accent-violet) 42%, transparent)', dot: 'var(--accent-violet)' }

  const chartData = (rows ?? []).map((r) => {
    const axis =
      r.shortTitle.length > 26 ? `${r.shortTitle.slice(0, 24)}…` : r.shortTitle
    const score =
      r.score == null || !Number.isFinite(Number(r.score)) ? min : Number(r.score)
    const fullLabel = [r.shortTitle, r.subtitle].filter(Boolean).join(' · ')
    return {
      axis,
      score,
      fullLabel: fullLabel || r.shortTitle,
    }
  })

  const hasAnyScore = (rows ?? []).some((r) => r.score != null && Number.isFinite(Number(r.score)))

  return (
    <section className="radarSection" aria-label={title}>
      <div className="radarSectionHead">
        <h2 className="radarHeading">{title}</h2>
      </div>

      <div className="radarChartWrap">
        <ResponsiveContainer width="100%" height={440}>
          <RadarChart cx="50%" cy="52%" outerRadius="72%" data={chartData}>
            <PolarGrid stroke="#cbd5e1" strokeDasharray="4 4" />
            <PolarAngleAxis
              dataKey="axis"
              tick={{ fill: '#475569', fontSize: chartData.length > 12 ? 9 : 10 }}
              tickLine={false}
            />
            <PolarRadiusAxis
              angle={90}
              domain={[min, max]}
              ticks={ticks}
              tick={{ fill: '#64748b', fontSize: 10 }}
              stroke="#94a3b8"
              axisLine={false}
            />
            <Tooltip content={(p) => <RadarTooltip {...p} framework={framework} />} />
            <Radar
              name="Overall Score"
              dataKey="score"
              stroke={palette.stroke}
              strokeWidth={2}
              fill={palette.fill}
              fillOpacity={0.38}
              dot={{ r: 3, fill: palette.dot, strokeWidth: 0 }}
              isAnimationActive
            />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="radarMaturityFooter">
        <div className="radarMaturityLabel">Maturity level</div>
        {!hasAnyScore || summaryValue == null ? (
          <div className="radarMaturityEmpty muted">
            Answer questions to see your overall maturity band.
          </div>
        ) : (
          <div className="radarMaturityValue">
            <strong>{summaryBandLabel}</strong>
            <span className="radarMaturityNum"> ({Number(summaryValue).toFixed(2)})</span>
          </div>
        )}
      </div>
    </section>
  )
}
