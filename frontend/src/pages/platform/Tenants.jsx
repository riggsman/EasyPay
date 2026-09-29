import { useEffect, useState } from 'react'
import { api } from '../../api/client'

export default function PlatformTenants() {
  const [rows, setRows] = useState([])
  useEffect(() => {
    api.tenants().then(setRows).catch(() => {})
  }, [])
  return (
    <div className="rise">
      <h2>Tenants / Councils</h2>
      <div className="panel table-wrap">
        <table className="data">
          <thead>
            <tr><th>Code</th><th>Name</th><th>Type</th><th>Currency</th><th>Zone change</th><th>Status</th></tr>
          </thead>
          <tbody>
            {rows.map((t) => (
              <tr key={t.tenant_id}>
                <td>{t.tenant_code}</td>
                <td>{t.organization_name}</td>
                <td>{t.organization_type}</td>
                <td>{t.currency}</td>
                <td>{t.zone_change_mode}</td>
                <td><span className="pill">{t.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
