import { fmtDate } from '../utils/formatters'

export default function DataStatusBanner({ status }) {
  if (!status) return null

  const colors = {
    ok: { bg: 'rgba(34,197,94,0.1)', border: '#22c55e', text: '#4ade80' },
    delayed: { bg: 'rgba(234,179,8,0.1)', border: '#eab308', text: '#fde047' },
    no_data: { bg: 'rgba(239,68,68,0.1)', border: '#ef4444', text: '#fca5a5' },
  }
  const c = colors[status.status] || colors.no_data

  return (
    <div style={{
      padding: '10px 16px',
      borderRadius: '8px',
      border: `1px solid ${c.border}`,
      background: c.bg,
      color: c.text,
      fontSize: '0.85rem',
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      flexWrap: 'wrap',
    }}>
      <span style={{ fontWeight: 700 }}>
        {status.status === 'ok' ? '✓ Ajantasalla' :
         status.status === 'delayed' ? '⚠ Viivästynyt' : '✗ Ei dataa'}
      </span>
      <span>{status.message}</span>
      {status.total_weeks > 0 && (
        <span style={{ marginLeft: 'auto', opacity: 0.8 }}>
          Yhteensä {status.total_weeks} viikkoa historiassa
        </span>
      )}
    </div>
  )
}
