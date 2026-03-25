import { useState } from 'react'

export default function InfoTip({ text }) {
  const [show, setShow] = useState(false)
  return (
    <span style={{ position: 'relative', display: 'inline-block', marginLeft: 4 }}>
      <span
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        style={{ cursor: 'help', color: '#475569', fontSize: '0.68rem', userSelect: 'none' }}
      >
        ⓘ
      </span>
      {show && (
        <div style={{
          position: 'absolute',
          bottom: '130%',
          left: '50%',
          transform: 'translateX(-50%)',
          background: '#1e293b',
          border: '1px solid #334155',
          borderRadius: 7,
          padding: '9px 13px',
          width: 230,
          fontSize: '0.75rem',
          color: '#94a3b8',
          lineHeight: 1.55,
          zIndex: 9999,
          whiteSpace: 'normal',
          pointerEvents: 'none',
          boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
        }}>
          {text}
        </div>
      )}
    </span>
  )
}
