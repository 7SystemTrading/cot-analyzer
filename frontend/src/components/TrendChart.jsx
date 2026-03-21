import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ReferenceLine, ResponsiveContainer
} from 'recharts'
import { fmtDate } from '../utils/formatters'

const COLORS = {
  currency_score: '#60a5fa',
  pair_score: '#60a5fa',
  percentile_52w: '#a78bfa',
  pair_percentile_52w: '#a78bfa',
  z_current: '#34d399',
  z_delta_1w: '#fbbf24',
  z_delta_4w: '#fb923c',
  z_oi_delta: '#f472b6',
}

const LABELS = {
  currency_score: 'CurrencyScore',
  pair_score: 'PairScore',
  percentile_52w: 'Percentile',
  pair_percentile_52w: 'Percentile',
  z_current: 'A – Positioning',
  z_delta_1w: 'B – 1vk momentum',
  z_delta_4w: 'C – 4vk momentum',
  z_oi_delta: 'D – Participation',
}

export default function TrendChart({ data, fields, title }) {
  if (!data || data.length === 0) {
    return (
      <div style={emptyStyle}>Ei historiaa saatavilla</div>
    )
  }

  const chartData = data.map(d => ({
    ...d,
    _date: fmtDate(d.report_date),
  }))

  return (
    <div>
      {title && <h3 style={{ color: '#e2e8f0', marginBottom: '12px', fontSize: '0.95rem' }}>{title}</h3>}
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: -10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis
            dataKey="_date"
            tick={{ fill: '#64748b', fontSize: 10 }}
            tickLine={false}
            interval="preserveStartEnd"
          />
          <YAxis
            tick={{ fill: '#64748b', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{ background: '#0f172a', border: '1px solid #334155', borderRadius: '6px' }}
            labelStyle={{ color: '#94a3b8', fontSize: '0.8rem' }}
            itemStyle={{ fontSize: '0.85rem' }}
            formatter={(val) => [val != null ? Number(val).toFixed(2) : '–']}
          />
          <Legend
            iconType="line"
            wrapperStyle={{ fontSize: '0.8rem', paddingTop: '8px' }}
          />
          <ReferenceLine y={0} stroke="#334155" strokeDasharray="4 4" />
          {fields.map(f => (
            <Line
              key={f}
              type="monotone"
              dataKey={f}
              name={LABELS[f] || f}
              stroke={COLORS[f] || '#94a3b8'}
              dot={false}
              strokeWidth={2}
              connectNulls={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

const emptyStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  height: '200px',
  color: '#475569',
  fontSize: '0.9rem',
}
