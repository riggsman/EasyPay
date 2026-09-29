import { useEffect, useState } from 'react'
import { api } from '../../api/client'

export default function ProfilePage() {
  const [payer, setPayer] = useState(null)
  const [area, setArea] = useState(null)

  useEffect(() => {
    Promise.all([api.mePayer(), api.operatingArea()]).then(([p, a]) => {
      setPayer(p)
      setArea(a)
    })
  }, [])

  if (!payer) return <p>Loading…</p>

  return (
    <div className="rise stack">
      <h2>My Profile</h2>
      <div className="panel">
        <h3>Identity</h3>
        <p><strong>{payer.full_name}</strong></p>
        <p>{payer.business_name}</p>
        <p className="muted">{payer.email} · {payer.phone_number}</p>
        <p className="muted">Ref: {payer.payer_reference}</p>
      </div>
      <div className="panel">
        <h3>Operating Information</h3>
        <p>{(area?.ancestry?.path || []).map((p) => p.name).join(' → ')}</p>
      </div>
    </div>
  )
}
