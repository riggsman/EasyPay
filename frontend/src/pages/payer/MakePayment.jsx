import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, listItems } from '../../api/client'

function productIcon(key) {
  if (key === 'council') return '🏛'
  if (key === 'utility') return '💡'
  if (key === 'droplet') return '💧'
  return '💳'
}

/**
 * Payment product chooser — driven by /payment-products/chooser.
 * New products appear here automatically when ACTIVE (and catalog-ready).
 */
export default function MakePaymentPage() {
  const navigate = useNavigate()
  const [products, setProducts] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    api.paymentProductsChooser()
      .then((rows) => setProducts(listItems(rows)))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  function openProduct(product) {
    if (!product.available) return
    navigate(product.route_path)
  }

  return (
    <div className="rise">
      <div className="app-top">
        <div>
          <h2>Make a payment</h2>
          <p className="muted">Choose what you want to pay. More payment types appear here as they are enabled.</p>
        </div>
      </div>
      {error && <div className="alert">{error}</div>}
      {loading && <p className="muted">Loading payment types…</p>}

      {!loading && (
        <div className="service-grid">
          {products.map((product) => {
            const unavailable = !product.available
            return (
              <button
                key={product.payment_product_id}
                type="button"
                className={`service-card${unavailable ? ' service-card--disabled' : ''}`}
                style={{ '--svc-accent': product.accent_color || '#1f6b4a' }}
                onClick={() => openProduct(product)}
                disabled={unavailable}
              >
                <span className="service-card-icon" aria-hidden="true">{productIcon(product.icon_key)}</span>
                <strong>{product.name}</strong>
                <span className="muted">{product.description}</span>
                {unavailable ? (
                  <span className="pill">Coming soon / unavailable</span>
                ) : product.requires_catalog ? (
                  <span className="pill">{product.catalog_count} service{product.catalog_count === 1 ? '' : 's'} available</span>
                ) : (
                  <span className="pill">Continue</span>
                )}
              </button>
            )
          })}
          {!products.length && (
            <div className="panel muted">No payment types are enabled right now.</div>
          )}
        </div>
      )}

      <p className="muted" style={{ marginTop: '1.5rem' }}>
        Looking for a past payment? <Link to="/payer/history">Open transaction history</Link>
      </p>
    </div>
  )
}
