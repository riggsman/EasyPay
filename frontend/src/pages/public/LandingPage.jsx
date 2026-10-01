import { Link } from 'react-router-dom'
import heroImage from '../../assets/landing-hero.jpg'

export default function LandingPage() {
  return (
    <>
      <section
        className="hero hero-fullbleed"
        style={{ '--hero-image': `url(${heroImage})` }}
      >
        <div className="hero-veil" aria-hidden="true" />
        <div className="container hero-copy">
          <div className="brand-hero rise">EasyPay</div>
          <h1 className="rise rise-delay-1">Pay your council levies</h1>
          <p className="rise rise-delay-2">
            Simple, secure, traceable payments from your registered operating area.
          </p>
          <div className="hero-actions rise rise-delay-3">
            <Link className="btn btn-sun" to="/register">Create Payer Account</Link>
            <Link className="btn btn-ghost hero-ghost" to="/login">Sign In</Link>
            <Link className="btn btn-ghost hero-ghost" to="/verify">Verify Receipt</Link>
          </div>
        </div>
      </section>

      <section className="section section-green" id="how">
        <div className="container">
          <h2>How it works</h2>
          <p>Register, select your council zone, view levies, pay, and verify your official receipt.</p>
          <ol className="steps">
            <li>Create Account</li>
            <li>Select Operating Council</li>
            <li>View Obligations</li>
            <li>Make Payment</li>
            <li>Receive Verified Receipt</li>
          </ol>
        </div>
      </section>

      <section className="section section-green-soft">
        <div className="container">
          <h2>Supported councils</h2>
          <p>Start with Southwest Region councils — including Kumba 1, Kumba 2, and Kumba 3.</p>
          <div className="row" style={{ marginTop: '1rem' }}>
            <span className="pill">Kumba 1</span>
            <span className="pill">Kumba 2</span>
            <span className="pill">Kumba 3</span>
          </div>
        </div>
      </section>
    </>
  )
}
