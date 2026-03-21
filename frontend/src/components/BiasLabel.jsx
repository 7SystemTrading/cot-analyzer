import { biasColor } from '../utils/formatters'

export default function BiasLabel({ label, size = 'sm' }) {
  if (!label) return <span style={{ color: '#94a3b8' }}>–</span>
  const color = biasColor(label)
  const fontSize = size === 'lg' ? '0.9rem' : '0.75rem'
  return (
    <span style={{
      display: 'inline-block',
      padding: size === 'lg' ? '4px 10px' : '2px 8px',
      borderRadius: '999px',
      border: `1px solid ${color}`,
      color,
      fontSize,
      fontWeight: 600,
      whiteSpace: 'nowrap',
    }}>
      {label}
    </span>
  )
}
