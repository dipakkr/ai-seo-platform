interface HighlightedTextProps {
  text: string
  terms: string[]
  className?: string
}

export default function HighlightedText({ text, terms, className }: HighlightedTextProps) {
  const cleanTerms = terms
    .map((term) => term.trim())
    .filter((term) => term.length >= 2)

  if (!cleanTerms.length || !text) {
    return <span className={className}>{text}</span>
  }

  const escaped = cleanTerms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const regex = new RegExp(`(${escaped.join('|')})`, 'gi')
  const parts = text.split(regex)

  return (
    <span className={className}>
      {parts.map((part, index) => {
        const isMatch = cleanTerms.some((term) => part.toLowerCase() === term.toLowerCase())
        if (!isMatch) {
          return <span key={`${part}-${index}`}>{part}</span>
        }
        return (
          <mark key={`${part}-${index}`} className="bg-yellow-100 text-neutral-900 px-0.5 rounded">
            {part}
          </mark>
        )
      })}
    </span>
  )
}
