import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

function yBounds(framework) {
  // UI rule: unanswered questions count as 0, so charts always include 0.
  return { min: 0, max: 5 }
}

function yTicks(framework) {
  return [0, 1, 2, 3, 4, 5]
}

function ChartTooltip({ active, payload, framework }) {
  if (!active || !payload?.length) return null
  const row = payload[0]?.payload
  if (!row) return null
  const { max } = yBounds(framework)
  return (
    <div className="chartTooltip">
      <div className="chartTooltipTitle">{row.label}</div>
      {row.hint ? <div className="chartTooltipSub">{row.hint}</div> : null}
      <div className="chartTooltipMeta">
        {row.score == null || Number.isNaN(row.score) ? (
          <span className="muted">No score yet</span>
        ) : (
          <>
            <strong>{row.score}</strong>
            <span className="chartTooltipSlash"> / {max}</span>
          </>
        )}
      </div>
    </div>
  )
}

/**
 * Scores along questions in the selected domain (reading order).
 */
export function SegmentQuestionsChart({ framework, points }) {
  const { min, max } = yBounds(framework)
  const ticks = yTicks(framework)
  const many = (points?.length ?? 0) > 12

  if (!points.length) return null

  return (
    <div className="chartBlock chartBlockCompact">
      <div className="chartBlockHeader">
        <div className="chartBlockTitle">This domain — question curve</div>
        <div className="chartBlockHint">
          Each point is one question in order. Empty gaps mean not scored yet.
        </div>
      </div>
      <div className="chartSvgWrap">
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={points} margin={{ top: 12, right: 12, left: 4, bottom: many ? 22 : 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="color-mix(in srgb, var(--border) 85%, transparent)" />
            <XAxis
              dataKey="shortLabel"
              tick={{ fontSize: 10, fill: 'var(--text-h)' }}
              tickLine={false}
              axisLine={{ stroke: 'var(--border)' }}
              interval={0}
              angle={many ? -30 : 0}
              textAnchor={many ? 'end' : 'middle'}
              height={many ? 48 : 32}
            />
            <YAxis
              domain={[min, max]}
              ticks={ticks}
              tick={{ fontSize: 11, fill: 'var(--text-h)' }}
              tickLine={false}
              axisLine={{ stroke: 'var(--border)' }}
              width={36}
            />
            <Tooltip content={(p) => <ChartTooltip framework={framework} {...p} />} />
            <Line
              type="monotone"
              dataKey="score"
              stroke="#0ea5e9"
              strokeWidth={2.5}
              dot={{ r: 3.5, fill: '#0ea5e9', strokeWidth: 0 }}
              activeDot={{ r: 5 }}
              connectNulls={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
