import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, formatMoney } from '../../api/client'
import { ChainSteps, Disclosure, MoneyCells, PageHeader } from '../../components/OpsUI'

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

  if (error) return <div className="alert">{error}</div>
  if (!txn) return <p>Loading…</p>

  return (
    <div className="rise stack">
      <PageHeader
        title={txn.transaction_reference}
        subtitle="Payment confirmation and full status timeline"
        actions={txn.receipt_id ? <Link className="btn btn-primary" to="/payer/receipts">Receipts</Link> : null}
      />
      <div className="row"><span className="pill">{txn.status}</span></div>
      <MoneyCells amount={txn.amount} fee={txn.service_fee} commission={txn.commission_amount} total={txn.total_amount} currency={txn.currency} />
      {txn.receipt_number && <p>Receipt: <strong>{txn.receipt_number}</strong></p>}
      {drill?.geography && <p className="muted">Zone at payment (immutable): {drill.geography.name}</p>}

      <Disclosure title="Transaction timeline" open>
        <div className="timeline">
          {(txn.events || []).map((e, i) => (
            <div className="item" key={i}>
              <strong>{e.to_status}</strong>
              <span className="muted">{e.note} · {new Date(e.created_at).toLocaleString()}</span>
            </div>
          ))}
        </div>
      </Disclosure>

      {drill && (
        <>
          <ChainSteps steps={drill.chain} active="transaction" />
          <Disclosure title="Fee breakdown">
            <p>
              Amount {formatMoney(drill.fee_commission ? txn.amount : txn.amount)} + service fee{' '}
              {formatMoney(txn.service_fee)} = total {formatMoney(txn.total_amount)}.
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
