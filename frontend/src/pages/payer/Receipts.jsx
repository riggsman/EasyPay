import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, formatMoney, listItems } from '../../api/client'

export default function ReceiptsPage() {
  const [rows, setRows] = useState([])
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState('')

  useEffect(() => {
    api.receipts({ page: 1, page_size: 100 }).then((res) => setRows(listItems(res))).catch((e) => setError(e.message))
  }, [])

  async function onDownload(r) {
    setError('')
    setBusyId(r.receipt_id)
    try {
      await api.downloadReceiptPdf(r.receipt_id, `${r.receipt_number}.pdf`)
    } catch (e) {
      setError(e.message || 'Download failed')
    } finally {
      setBusyId('')
    }
  }

  return (
    <div className="rise">
      <h2>Receipts</h2>
      {error && <div className="alert">{error}</div>}
      <div className="panel table-wrap">
        <table className="data">
          <thead>
            <tr>
              <th>Receipt</th>
              <th>Council</th>
              <th>Revenue</th>
              <th>Total</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.receipt_id}>
                <td>{r.receipt_number}</td>
                <td>{r.council_name}</td>
                <td>{r.revenue_name}</td>
                <td>{formatMoney(r.total_amount, r.currency)}</td>
                <td><span className="pill">{r.status}</span></td>
                <td>
                  <div className="row" style={{ gap: '0.5rem', justifyContent: 'flex-end' }}>
                    {r.pdf_download_url && r.status !== 'REVOKED' && (
                      <button
                        className="btn btn-primary"
                        type="button"
                        disabled={busyId === r.receipt_id}
                        onClick={() => onDownload(r)}
                      >
                        {busyId === r.receipt_id ? 'Downloading…' : 'Download receipt'}
                      </button>
                    )}
                    <Link className="btn btn-ghost" to="/verify">Verify</Link>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
