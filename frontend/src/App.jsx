import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { PublicLayout, PayerLayout, TenantLayout, PlatformLayout } from './layouts/Layouts'
import LandingPage from './pages/public/LandingPage'
import LoginPage from './pages/public/LoginPage'
import RegisterPage from './pages/public/RegisterPage'
import VerifyPage from './pages/public/VerifyPage'
import PayerDashboard from './pages/payer/Dashboard'
import ObligationsPage from './pages/payer/Obligations'
import MakePaymentPage from './pages/payer/MakePayment'
import PaymentHistory from './pages/payer/PaymentHistory'
import PaymentDetail from './pages/payer/PaymentDetail'
import ReceiptsPage from './pages/payer/Receipts'
import OperatingAreaPage from './pages/payer/OperatingArea'
import ProfilePage from './pages/payer/Profile'
import TenantDashboard from './pages/tenant/Dashboard'
import TenantTransactions from './pages/tenant/Transactions'
import TenantSettlements from './pages/tenant/Settlements'
import TenantReports from './pages/tenant/Reports'
import TenantObligations from './pages/tenant/Obligations'
import TenantRevenue from './pages/tenant/Revenue'
import PlatformDashboard from './pages/platform/Dashboard'
import PlatformTenants from './pages/platform/Tenants'
import PlatformGeography from './pages/platform/Geography'
import PlatformReports from './pages/platform/Reports'

function RequireAuth({ allow }) {
  const { isAuthenticated, userType } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (allow && !allow.includes(userType)) {
    if (userType === 'PAYER') return <Navigate to="/payer" replace />
    if (userType === 'PLATFORM_ADMIN') return <Navigate to="/platform" replace />
    return <Navigate to="/tenant" replace />
  }
  return <Outlet />
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/verify" element={<VerifyPage />} />
        </Route>

        <Route element={<RequireAuth allow={['PAYER']} />}>
          <Route element={<PayerLayout />}>
            <Route path="/payer" element={<PayerDashboard />} />
            <Route path="/payer/obligations" element={<ObligationsPage />} />
            <Route path="/payer/pay" element={<MakePaymentPage />} />
            <Route path="/payer/history" element={<PaymentHistory />} />
            <Route path="/payer/payments/:id" element={<PaymentDetail />} />
            <Route path="/payer/receipts" element={<ReceiptsPage />} />
            <Route path="/payer/area" element={<OperatingAreaPage />} />
            <Route path="/payer/profile" element={<ProfilePage />} />
          </Route>
        </Route>

        <Route element={<RequireAuth allow={['STAFF', 'PLATFORM_ADMIN']} />}>
          <Route element={<TenantLayout />}>
            <Route path="/tenant" element={<TenantDashboard />} />
            <Route path="/tenant/obligations" element={<TenantObligations />} />
            <Route path="/tenant/revenue" element={<TenantRevenue />} />
            <Route path="/tenant/transactions" element={<TenantTransactions />} />
            <Route path="/tenant/settlements" element={<TenantSettlements />} />
            <Route path="/tenant/reports" element={<TenantReports />} />
          </Route>
        </Route>

        <Route element={<RequireAuth allow={['PLATFORM_ADMIN']} />}>
          <Route element={<PlatformLayout />}>
            <Route path="/platform" element={<PlatformDashboard />} />
            <Route path="/platform/tenants" element={<PlatformTenants />} />
            <Route path="/platform/geography" element={<PlatformGeography />} />
            <Route path="/platform/reports" element={<PlatformReports />} />
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
