import { useId, useState } from 'react'

function yBounds(framework) {
  // UI rule: unanswered questions count as 0, so charts always include 0.
  return { min: 0, max: 5 }
}

function tickValues(framework) {
  return [0, 1, 2, 3, 4, 5]
}

/**
 * Lightweight pseudo-3D plot: skewed “floor”, vertical maturity axis, single marker.
 */
function Pseudo3DScoreMarker({ framework, score }) {
  const { min, max } = yBounds(framework)
  const ticks = tickValues(framework)
  const hasScore = score != null && Number.isFinite(Number(score))
  const num = hasScore ? Number(score) : null

  const w = 220
  const h = 132
  const yBottom = 106
  const yTop = 26
  const xAxisLeft = 34
  const xFloorRight = 162
  const xBack = 172

  const t =
    hasScore && num != null ? Math.min(1, Math.max(0, (num - min) / (max - min || 1))) : 0
  const dotY = yBottom - t * (yBottom - yTop)
  const dotX = 96 + Math.sin(t * Math.PI) * 10

  const gradId = useId().replace(/:/g, '')

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="pseudo3dSvg" aria-hidden={!hasScore}>
      <defs>
        <linearGradient id={`floor-${gradId}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#f8fafc" />
          <stop offset="100%" stopColor="#e2e8f0" />
        </linearGradient>
      </defs>

      <path
        d={`M ${xAxisLeft - 4} ${yBottom - 2} L ${xFloorRight} ${yBottom + 4} L ${xBack} ${yBottom - 18} L ${xAxisLeft + 18} ${yBottom - 22} Z`}
        fill={`url(#floor-${gradId})`}
        stroke="#e2e8f0"
        strokeWidth="1"
      />

      <line
        x1={xAxisLeft}
        y1={yBottom}
        x2={xAxisLeft}
        y2={yTop}
        stroke="#64748b"
        strokeWidth="2.2"
        strokeLinecap="round"
      />

      <line
        x1={xAxisLeft}
        y1={yBottom}
        x2={xFloorRight}
        y2={yBottom + 5}
        stroke="#94a3b8"
        strokeWidth="1.5"
      />

      <line
        x1={xFloorRight}
        y1={yBottom + 5}
        x2={xBack}
        y2={yBottom - 14}
        stroke="#cbd5e1"
        strokeWidth="1"
      />

      <line
        x1={xAxisLeft}
        y1={yTop}
        x2={xFloorRight - 10}
        y2={yTop + 8}
        stroke="#e2e8f0"
        strokeWidth="1"
      />

      <line
        x1={xFloorRight - 10}
        y1={yTop + 8}
        x2={xFloorRight}
        y2={yBottom + 5}
        stroke="#e2e8f0"
        strokeWidth="1"
      />

      {ticks.map((tv) => {
        const tt = (tv - min) / (max - min || 1)
        const ty = yBottom - tt * (yBottom - yTop)
        return (
          <g key={tv}>
            <line
              x1={xAxisLeft - 2}
              y1={ty}
              x2={xAxisLeft + 5}
              y2={ty}
              stroke="#cbd5e1"
              strokeWidth="1"
            />
            <text
              x={xAxisLeft - 8}
              y={ty + 4}
              textAnchor="end"
              fontSize="9"
              fill="#64748b"
              fontFamily="system-ui, sans-serif"
            >
              {tv}
            </text>
          </g>
        )
      })}

      {hasScore ? (
        <>
          <circle cx={dotX} cy={dotY} r="12" fill="rgba(37, 99, 235, 0.12)" />
          <circle cx={dotX} cy={dotY} r="7" fill="#2563eb" stroke="#fff" strokeWidth="2" />
        </>
      ) : (
        <text
          x={w / 2}
          y={yBottom - 38}
          textAnchor="middle"
          fontSize="11"
          fill="#94a3b8"
          fontFamily="system-ui, sans-serif"
        >
          No score yet
        </text>
      )}
    </svg>
  )
}

function DomainCard({ framework, shortTitle, subtitle, score }) {
  const [hover, setHover] = useState(false)
  const { max } = yBounds(framework)
  const display =
    score != null && Number.isFinite(Number(score))
      ? Math.round(Number(score) * 100) / 100
      : null

  return (
    <div
      className="domainAnalysisCard"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <h3 className="domainAnalysisCardTitle">{shortTitle}</h3>
      <p className="domainAnalysisCardSub" title={subtitle}>
        {subtitle}
      </p>
      <div className="domainAnalysisCardChart">
        <Pseudo3DScoreMarker framework={framework} score={score} />
        {hover && display != null ? (
          <div className="domainAnalysisTooltip" role="tooltip">
            <span className="domainAnalysisTooltipLabel">Current maturity</span>
            <span className="domainAnalysisTooltipValue">
              {display} / {max}
            </span>
          </div>
        ) : null}
      </div>
    </div>
  )
}

/**
 * Card grid in the style of “Domain Specific Analysis”: one 3D-style plot per domain.
 */
export function DomainSpecificAnalysis({ framework, items }) {
  if (!items?.length) return null

  return (
    <section className="domainAnalysisSection" aria-label="Domain specific analysis">
      <h2 className="domainAnalysisHeading">Domain Specific Analysis</h2>
      <p className="domainAnalysisLead">
        Each card shows the current average for that domain ({framework === 'ndi' ? 'NDI 0–5' : 'CMMI 1–5'}). Hover the
        marker for the exact value.
      </p>
      <div className="domainAnalysisGrid">
        {items.map((item) => (
          <DomainCard
            key={item.key}
            framework={framework}
            shortTitle={item.shortTitle}
            subtitle={item.subtitle}
            score={item.score}
          />
        ))}
      </div>
    </section>
  )
}
