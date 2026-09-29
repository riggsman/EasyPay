import { useEffect, useState } from 'react'
import { api, formatMoney } from '../../api/client'

export default function TenantReports() {
  const [report, setReport] = useState(null)
  useEffect(() => {
    api.collectionsReport().then(setReport).catch(() => {})
  }, [])
  return (
    <div className="rise stack">
      <h2>Collections Report</h2>
      <p className="muted">Aggregates use transaction location snapshots — never the payer’s current zone.</p>
      {report && (
        <div className="stat-grid">
          <div className="panel stat"><span className="muted">Gross</span><strong>{formatMoney(report.gross_collections)}</strong></div>
          <div className="panel stat"><span className="muted">Fees</span><strong>{formatMoney(report.service_fees)}</strong></div>
          <div className="panel stat"><span className="muted">Commission</span><strong>{formatMoney(report.commission)}</strong></div>
          <div className="panel stat"><span className="muted">Net</span><strong>{formatMoney(report.net_settlement)}</strong></div>
        </div>
      )}
      <div className="panel table-wrap">
        <table className="data">
          <thead>
            <tr><th>Reference</th><th>Amount</th><th>Geo snapshot</th><th>Settled</th></tr>
          </thead>
          <tbody>
            {(report?.transactions || []).map((t) => (
              <tr key={t.transaction_id}>
                <td>{t.reference}</td>
                <td>{formatMoney(t.amount)}</td>
                <td className="muted">{t.geographic_unit_id}</td>
                <td>{t.settled_at ? new Date(t.settled_at).toLocaleString() : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
