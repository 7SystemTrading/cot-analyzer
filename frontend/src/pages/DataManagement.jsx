import { useEffect, useState } from 'react'
import { getDataStatus, fetchData, getConfig, updateConfig } from '../api/client'
import { fmtDate } from '../utils/formatters'

const S = {
  page:   { maxWidth: 800 },
  title:  { fontSize: '1.4rem', fontWeight: 700, color: '#e2e8f0', marginBottom: 24 },
  card:   { background: '#0f172a', border: '1px solid #1e293b', borderRadius: 10, padding: '20px', marginBottom: 20 },
  label:  { fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: '#64748b', marginBottom: 8 },
  btn:    { padding: '8px 20px', borderRadius: 7, border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: '0.85rem', transition: 'opacity 0.15s' },
  input:  { background: '#1e293b', border: '1px solid #334155', borderRadius: 6, color: '#e2e8f0', padding: '7px 12px', fontSize: '0.85rem', width: 100 },
}

const DEFAULT_CFG = {
  percentile_window: 156, divergence_window: 4,
  weight_direction: 0.4, weight_momentum: 0.2, weight_strength: 0.4,
  extreme_threshold_mild: 0.70, extreme_threshold_major: 0.85, extreme_threshold_historic: 0.95,
}

export default function DataManagement() {
  const [status, setStatus]   = useState(null)
  const [loading, setLoading] = useState(true)
  const [fetching, setFetching] = useState(false)
  const [year, setYear] = useState('')
  const [msg, setMsg]   = useState(null)
  const [cfg, setCfg]         = useState(DEFAULT_CFG)
  const [cfgSaving, setCfgSaving] = useState(false)
  const [cfgMsg, setCfgMsg]   = useState(null)

  const loadStatus = async () => {
    try {
      const res = await getDataStatus()
      setStatus(res.data)
    } catch {}
    setLoading(false)
  }

  useEffect(() => {
    loadStatus()
    getConfig().then(r => setCfg(r.data)).catch(() => {})
  }, [])

  const doFetch = async () => {
    setFetching(true)
    setMsg(null)
    try {
      await fetchData(year ? parseInt(year) : null)
      setMsg({ ok: true, text: 'Fetch started in background. Refresh status in a moment.' })
      setTimeout(loadStatus, 5000)
    } catch (e) {
      setMsg({ ok: false, text: `Error: ${e.message}` })
    } finally {
      setFetching(false)
    }
  }

  const saveCfg = async () => {
    setCfgSaving(true)
    setCfgMsg(null)
    try {
      await updateConfig(cfg)
      setCfgMsg({ ok: true, text: 'Settings saved. Recalculation running in background...' })
    } catch (e) {
      setCfgMsg({ ok: false, text: `Error: ${e.message}` })
    } finally {
      setCfgSaving(false)
    }
  }

  const cfgField = (key, label, min, max, step = 0.01) => (
    <div key={key} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      <label style={{ fontSize: '0.72rem', color: '#64748b', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</label>
      <input type="number" min={min} max={max} step={step}
        value={cfg[key] ?? ''} onChange={e => setCfg(c => ({ ...c, [key]: parseFloat(e.target.value) }))}
        style={{ ...S.input, width: 90 }} />
    </div>
  )

  return (
    <div style={S.page}>
      <h1 style={S.title}>Data Management</h1>

      {/* Status */}
      <div style={S.card}>
        <div style={S.label}>Database Status</div>
        {loading ? (
          <div style={{ color: '#64748b' }}>Loading...</div>
        ) : status ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 16 }}>
            {[
              ['Latest Report', fmtDate(status.latest_report_date)],
              ['Total Weeks', status.total_weeks],
              ['Total Rows', status.total_rows],
              ['Currencies', (status.currencies_covered || []).join(', ')],
            ].map(([l, v]) => (
              <div key={l}>
                <div style={{ fontSize: '0.72rem', color: '#64748b', marginBottom: 4 }}>{l}</div>
                <div style={{ color: '#e2e8f0', fontWeight: 600 }}>{v}</div>
              </div>
            ))}
          </div>
        ) : (
          <div style={{ color: '#64748b' }}>No data yet</div>
        )}
      </div>

      {/* Fetch */}
      <div style={S.card}>
        <div style={S.label}>Fetch CFTC Data</div>
        <p style={{ color: '#94a3b8', fontSize: '0.85rem', marginBottom: 16, lineHeight: 1.6 }}>
          Fetches Legacy COT data from CFTC. Leave year empty to fetch the latest available data.
          Full history fetch (3 years) happens automatically on first start.
        </p>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <input
            type="number" placeholder="Year (optional)"
            value={year} onChange={e => setYear(e.target.value)}
            style={S.input} min={2000} max={new Date().getFullYear()}
          />
          <button
            style={{ ...S.btn, background: '#1e3a5f', color: '#e2e8f0', opacity: fetching ? 0.6 : 1 }}
            onClick={doFetch} disabled={fetching}>
            {fetching ? 'Starting...' : 'Fetch Data'}
          </button>
          <button
            style={{ ...S.btn, background: '#0f172a', color: '#64748b', border: '1px solid #334155' }}
            onClick={loadStatus}>
            Refresh Status
          </button>
        </div>
        {msg && (
          <div style={{ marginTop: 12, color: msg.ok ? '#22c55e' : '#ef4444', fontSize: '0.85rem' }}>
            {msg.text}
          </div>
        )}
      </div>

      {/* Settings §16 */}
      <div style={S.card}>
        <div style={S.label}>Calculation Settings</div>
        <p style={{ color: '#94a3b8', fontSize: '0.82rem', marginBottom: 16, lineHeight: 1.6 }}>
          Changes trigger a full recalculation in the background. Score weights must sum to 1.0.
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 16, marginBottom: 16 }}>
          {cfgField('percentile_window',          'History Window (weeks)', 52, 520, 1)}
          {cfgField('divergence_window',          'Divergence Window (weeks)', 2, 12, 1)}
          {cfgField('weight_direction',           'Weight: Direction', 0, 1)}
          {cfgField('weight_momentum',            'Weight: Momentum', 0, 1)}
          {cfgField('weight_strength',            'Weight: Strength', 0, 1)}
          {cfgField('extreme_threshold_mild',     'Extreme: Mild threshold', 0.5, 0.9)}
          {cfgField('extreme_threshold_major',    'Extreme: Major threshold', 0.6, 0.95)}
          {cfgField('extreme_threshold_historic', 'Extreme: Historic threshold', 0.7, 0.99)}
        </div>
        <button
          style={{ ...S.btn, background: '#1e3a5f', color: '#e2e8f0', opacity: cfgSaving ? 0.6 : 1 }}
          onClick={saveCfg} disabled={cfgSaving}>
          {cfgSaving ? 'Saving...' : 'Save & Recalculate'}
        </button>
        {cfgMsg && (
          <div style={{ marginTop: 10, color: cfgMsg.ok ? '#22c55e' : '#ef4444', fontSize: '0.82rem' }}>
            {cfgMsg.text}
          </div>
        )}
      </div>

      {/* Import logs */}
      {status?.recent_logs?.length > 0 && (
        <div style={S.card}>
          <div style={S.label}>Recent Import Logs</div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.82rem' }}>
            <thead>
              <tr>
                {['Date', 'Type', 'Inserted', 'Skipped', 'Status'].map(h => (
                  <th key={h} style={{ textAlign: 'left', padding: '6px 10px', color: '#64748b',
                    borderBottom: '1px solid #1e293b', fontWeight: 600 }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {status.recent_logs.map(lg => (
                <tr key={lg.id}>
                  <td style={{ padding: '6px 10px', color: '#94a3b8' }}>{lg.imported_at?.slice(0, 16)}</td>
                  <td style={{ padding: '6px 10px', color: '#94a3b8' }}>{lg.source_type}</td>
                  <td style={{ padding: '6px 10px', color: '#22c55e' }}>{lg.rows_inserted}</td>
                  <td style={{ padding: '6px 10px', color: '#64748b' }}>{lg.rows_skipped}</td>
                  <td style={{ padding: '6px 10px', color: lg.status === 'ok' ? '#22c55e' : '#ef4444', fontWeight: 600 }}>
                    {lg.status}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
