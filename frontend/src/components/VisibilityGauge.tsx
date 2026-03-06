interface Props {
  score: number
  size?: 'sm' | 'lg'
}

function scoreColor(score: number): string {
  if (score < 30) return '#ef4444'  // red-500
  if (score < 60) return '#eab308'  // yellow-500
  return '#22c55e'  // green-500
}

function scoreBgClass(score: number): string {
  if (score < 30) return 'bg-red-50'
  if (score < 60) return 'bg-yellow-50'
  return 'bg-green-50'
}

function scoreTextClass(score: number): string {
  if (score < 30) return 'text-red-600'
  if (score < 60) return 'text-yellow-600'
  return 'text-green-600'
}

export default function VisibilityGauge({ score, size = 'lg' }: Props) {
  const radius = size === 'lg' ? 80 : 40
  const stroke = size === 'lg' ? 12 : 8
  const normalizedRadius = radius - stroke / 2
  const circumference = normalizedRadius * Math.PI // semicircle
  const offset = circumference - (score / 100) * circumference
  const svgSize = radius * 2
  const color = scoreColor(score)

  if (size === 'sm') {
    return (
      <div className={`inline-flex items-center justify-center w-16 h-16 rounded-full ${scoreBgClass(score)}`}>
        <span className={`text-xl font-bold ${scoreTextClass(score)}`}>{Math.round(score)}</span>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-center">
      <svg width={svgSize} height={radius + stroke} className="overflow-visible">
        {/* Background arc */}
        <path
          d={describeArc(radius, radius, normalizedRadius, 180, 360)}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        {/* Score arc */}
        <path
          d={describeArc(radius, radius, normalizedRadius, 180, 180 + (score / 100) * 180)}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          style={{
            transition: 'stroke-dashoffset 0.8s ease-in-out',
            strokeDasharray: circumference,
            strokeDashoffset: offset,
          }}
        />
        <text
          x={radius}
          y={radius - 4}
          textAnchor="middle"
          className="fill-gray-900"
          fontSize={size === 'lg' ? 36 : 20}
          fontWeight="bold"
        >
          {Math.round(score)}
        </text>
        <text
          x={radius}
          y={radius + 16}
          textAnchor="middle"
          className="fill-gray-400"
          fontSize={12}
        >
          / 100
        </text>
      </svg>
      <p className={`mt-1 text-sm font-medium ${scoreTextClass(score)}`}>
        {score < 30 ? 'Low Visibility' : score < 60 ? 'Moderate Visibility' : 'Strong Visibility'}
      </p>
    </div>
  )
}

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const angleRad = ((angleDeg - 90) * Math.PI) / 180
  return {
    x: cx + r * Math.cos(angleRad),
    y: cy + r * Math.sin(angleRad),
  }
}

function describeArc(cx: number, cy: number, r: number, startAngle: number, endAngle: number) {
  const start = polarToCartesian(cx, cy, r, endAngle)
  const end = polarToCartesian(cx, cy, r, startAngle)
  const largeArcFlag = endAngle - startAngle <= 180 ? '0' : '1'
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`
}
