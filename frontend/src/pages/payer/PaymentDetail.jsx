import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, formatMoney } from '../../api/client'
import { ChainSteps, Disclosure, MoneyCells, PageHeader, TransactionTimeline } from '../../components/OpsUI'

export default function PaymentDetail() {
  const { id } = useParams()
  const [txn, setTxn] = useState(null)
  const [drill, setDrill] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.payment(id), api.opsDrillTransaction(id).catch(() => null)])
      .then(([t, d]) => {
        setTxn(t)
        setDrill(d)
      })
      .catch((e) => setError(e.message))
  }, [id])

  useEffect(() => {
    function onRealtime(e) {
      const msg = e.detail
      if (msg?.type !== 'transaction.status_changed') return
      if (msg.entity_id !== id && msg.payload?.transaction_id !== id) return
      api.payment(id).then(setTxn).catch(() => {})
    }
    window.addEventListener('ep:realtime', onRealtime)
    return () => window.removeEventListener('ep:realtime', onRealtime)
  }, [id])

  if (error) return <div className="alert">{error}</div>
  if (!txn) return <p>Loading…</p>

  return (
    <div className="rise stack">
      <PageHeader
        title={txn.transaction_reference}
        subtitle="Payment confirmation and full status timeline"
        actions={(
          <div className="row">
            {txn.receipt_pdf_url && (
              <button
                className="btn btn-primary"
                type="button"
                onClick={() => api.downloadReceiptPdf(txn.receipt_id, `${txn.receipt_number || 'receipt'}.pdf`).catch((e) => setError(e.message))}
              >
                Download receipt
              </button>
            )}
            {txn.receipt_id ? <Link className="btn btn-ghost" to="/payer/receipts">Receipts</Link> : null}
          </div>
        )}
      />
      <div className="row">
        <span className={`pill${['FAILED', 'REJECTED', 'MANUAL_INTERVENTION'].includes(txn.status) ? ' failed' : ''}`}>
          {txn.status === 'REJECTED' ? 'FAILED' : txn.status}
        </span>
      </div>
      {txn.failure_reason && (
        <Disclosure title="View failure reason" open>
          <p className="failure-reason-inline">{txn.failure_reason}</p>
          {txn.failure_stage && <p className="muted">Failed at: {txn.failure_stage}</p>}
        </Disclosure>
      )}
      <MoneyCells
        amount={txn.amount}
        fee={txn.service_fee}
        total={txn.total_amount}
        currency={txn.currency}
        showCommission={false}
      />
      {txn.receipt_number && <p>Receipt: <strong>{txn.receipt_number}</strong></p>}
      {drill?.geography && <p className="muted">Zone at payment (immutable): {drill.geography.name}</p>}

      <Disclosure title="Transaction timeline" open>
        <TransactionTimeline events={txn.events} failureReason={txn.failure_reason} />
      </Disclosure>

      {drill && (
        <>
          <ChainSteps steps={drill.chain} active="transaction" />
          <Disclosure title="Fee breakdown">
            <p>
              Amount {formatMoney(txn.amount)} + service fee {formatMoney(txn.service_fee)} = total{' '}
              {formatMoney(txn.total_amount)}.
            </p>
          </Disclosure>
        </>
      )}

      <div className="row">
        <Link className="btn btn-ghost" to="/verify">Verify Receipt</Link>
        <Link className="btn btn-ghost" to="/payer/history">Payment history</Link>
      </div>
    </div>
  )
}
