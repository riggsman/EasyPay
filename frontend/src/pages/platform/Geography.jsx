import { useEffect, useState } from 'react'
import { api } from '../../api/client'

export default function PlatformGeography() {
  const [tree, setTree] = useState([])

  useEffect(() => {
    ;(async () => {
      async function walk(parentId, depth = 0) {
        const kids = await api.geographyChildren(parentId)
        const out = []
        for (const k of kids) {
          out.push({ ...k, depth })
          out.push(...(await walk(k.geographic_unit_id, depth + 1)))
        }
        return out
      }
      setTree(await walk(null))
    })().catch(() => {})
  }, [])

  return (
    <div className="rise">
      <h2>Geographic Hierarchy</h2>
      <div className="panel">
        {tree.map((u) => (
          <div key={u.geographic_unit_id} style={{ paddingLeft: u.depth * 18, padding: '0.35rem 0' }}>
            <strong>{u.unit_name}</strong>{' '}
            <span className="muted">{u.unit_code} · {u.unit_type}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
