import { Link } from 'react-router-dom'
import { formatMoney } from '../api/client'

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="app-top">
      <div>
        <h2>{title}</h2>
        {subtitle && <p className="muted">{subtitle}</p>}
      </div>
      {actions && <div className="row">{actions}</div>}
    </div>
  )
}

export function StatLink({ to, label, value }) {
  const inner = (
    <>
      <span className="muted">{label}</span>
      <strong>{value}</strong>
    </>
  )
  if (to) return <Link className="panel stat drill" to={to}>{inner}</Link>
  return <div className="panel stat">{inner}</div>
}

export function Disclosure({ title, children, open = false }) {
  return (
    <details className="details-block" open={open}>
      <summary>{title}</summary>
      <div style={{ marginTop: '0.75rem' }}>{children}</div>
    </details>
  )
}

export function ChainSteps({ steps, active }) {
  return (
    <div className="chain-steps">
      {steps.map((s, i) => (
        <span key={s} className={`chain-step ${active === s || active === i ? 'on' : ''}`}>
          {s}
          {i < steps.length - 1 ? ' → ' : ''}
        </span>
      ))}
    </div>
  )
}

export function MoneyCells({ amount, fee, commission, total, currency = 'XAF' }) {
  return (
    <div className="stat-grid">
      <div className="stat"><span className="muted">Amount</span><strong>{formatMoney(amount, currency)}</strong></div>
      <div className="stat"><span className="muted">Service fee</span><strong>{formatMoney(fee, currency)}</strong></div>
      <div className="stat"><span className="muted">Commission</span><strong>{formatMoney(commission, currency)}</strong></div>
      <div className="stat"><span className="muted">Total</span><strong>{formatMoney(total ?? Number(amount || 0) + Number(fee || 0), currency)}</strong></div>
    </div>
  )
}

export function EmptyRow({ cols, text = 'No records.' }) {
  return (
    <tr>
      <td colSpan={cols} className="muted">{text}</td>
    </tr>
  )
}

export function PaginationBar({ page, totalPages, total, pageSize, onPageChange, onPageSizeChange }) {
  if (!total && page === 1) return null
  return (
    <div className="row" style={{ justifyContent: 'space-between', marginTop: '0.75rem', flexWrap: 'wrap', gap: '0.5rem' }}>
      <span className="muted">
        Page {page} of {Math.max(totalPages, 1)} · {total} total
      </span>
      <div className="row">
        {onPageSizeChange && (
          <select value={pageSize} onChange={(e) => onPageSizeChange(Number(e.target.value))} aria-label="Page size">
            {[10, 25, 50, 100].map((n) => (
              <option key={n} value={n}>{n} / page</option>
            ))}
          </select>
        )}
        <button className="btn btn-ghost" type="button" disabled={page <= 1} onClick={() => onPageChange(page - 1)}>
          Previous
        </button>
        <button className="btn btn-ghost" type="button" disabled={page >= totalPages} onClick={() => onPageChange(page + 1)}>
          Next
        </button>
      </div>
    </div>
  )
}
