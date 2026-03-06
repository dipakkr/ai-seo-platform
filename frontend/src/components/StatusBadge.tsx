interface Props {
  label: string
  variant?: 'gray' | 'green' | 'red' | 'yellow' | 'blue' | 'purple' | 'indigo' | 'orange'
}

const variantStyles: Record<string, string> = {
  gray: 'bg-gray-100 text-gray-700',
  green: 'bg-green-100 text-green-700',
  red: 'bg-red-100 text-red-700',
  yellow: 'bg-yellow-100 text-yellow-700',
  blue: 'bg-blue-100 text-blue-700',
  purple: 'bg-purple-100 text-purple-700',
  indigo: 'bg-indigo-100 text-indigo-700',
  orange: 'bg-orange-100 text-orange-700',
}

export default function StatusBadge({ label, variant = 'gray' }: Props) {
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${variantStyles[variant]}`}
    >
      {label}
    </span>
  )
}

export function intentBadgeVariant(
  intent: string
): 'blue' | 'purple' | 'orange' | 'green' | 'gray' {
  switch (intent) {
    case 'discovery':
      return 'blue'
    case 'comparison':
      return 'purple'
    case 'problem':
      return 'orange'
    case 'recommendation':
      return 'green'
    default:
      return 'gray'
  }
}

export function opportunityBadgeVariant(
  type: string
): 'red' | 'orange' | 'yellow' | 'purple' | 'gray' {
  switch (type) {
    case 'invisible':
      return 'red'
    case 'competitor_dominated':
      return 'orange'
    case 'partial_visibility':
      return 'yellow'
    case 'negative_sentiment':
      return 'purple'
    default:
      return 'gray'
  }
}

export function scanStatusVariant(
  status: string
): 'gray' | 'blue' | 'green' | 'red' {
  switch (status) {
    case 'pending':
      return 'gray'
    case 'running':
      return 'blue'
    case 'completed':
      return 'green'
    case 'failed':
      return 'red'
    default:
      return 'gray'
  }
}
