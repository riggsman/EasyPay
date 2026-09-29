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
import TenantObligations from './pages/tenant/Obligations'
import TenantRevenue from './pages/tenant/Revenue'
import PlatformTenants from './pages/platform/Tenants'
import PlatformGeography from './pages/platform/Geography'
import {
  OpsDashboard,
  OpsAlerts,
  OpsPayers,
  OpsCollections,
  OpsTransactions,
  OpsLedger,
  OpsReceipts,
  OpsFees,
  OpsCommissions,
  OpsUsersRoles,
  OpsConfig,
  OpsReconciliation,
  OpsStatements,
  OpsAudit,
  OpsSettlements,
  OpsReports,
} from './pages/ops/OpsPages'

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

function tenantOpsRoutes() {
  return (
    <>
      <Route path="/tenant" element={<OpsDashboard mode="tenant" />} />
      <Route path="/tenant/alerts" element={<OpsAlerts />} />
      <Route path="/tenant/users" element={<OpsUsersRoles />} />
      <Route path="/tenant/revenue" element={<TenantRevenue />} />
      <Route path="/tenant/fees" element={<OpsFees />} />
      <Route path="/tenant/commissions" element={<OpsCommissions />} />
      <Route path="/tenant/config" element={<OpsConfig />} />
      <Route path="/tenant/payers" element={<OpsPayers />} />
      <Route path="/tenant/obligations" element={<TenantObligations />} />
      <Route path="/tenant/collections" element={<OpsCollections />} />
      <Route path="/tenant/transactions" element={<OpsTransactions />} />
      <Route path="/tenant/ledger" element={<OpsLedger />} />
      <Route path="/tenant/receipts" element={<OpsReceipts />} />
      <Route path="/tenant/settlements" element={<OpsSettlements />} />
      <Route path="/tenant/reconciliation" element={<OpsReconciliation />} />
      <Route path="/tenant/statements" element={<OpsStatements />} />
      <Route path="/tenant/reports" element={<OpsReports />} />
      <Route path="/tenant/audit" element={<OpsAudit />} />
    </>
  )
}

function platformOpsRoutes() {
  return (
    <>
      <Route path="/platform" element={<OpsDashboard mode="platform" />} />
      <Route path="/platform/alerts" element={<OpsAlerts />} />
      <Route path="/platform/tenants" element={<PlatformTenants />} />
      <Route path="/platform/geography" element={<PlatformGeography />} />
      <Route path="/platform/users" element={<OpsUsersRoles />} />
      <Route path="/platform/config" element={<OpsConfig />} />
      <Route path="/platform/payers" element={<OpsPayers />} />
      <Route path="/platform/transactions" element={<OpsTransactions />} />
      <Route path="/platform/collections" element={<OpsCollections />} />
      <Route path="/platform/ledger" element={<OpsLedger />} />
      <Route path="/platform/receipts" element={<OpsReceipts />} />
      <Route path="/platform/settlements" element={<OpsSettlements />} />
      <Route path="/platform/reconciliation" element={<OpsReconciliation />} />
      <Route path="/platform/reports" element={<OpsReports />} />
      <Route path="/platform/audit" element={<OpsAudit />} />
    </>
  )
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
          <Route element={<TenantLayout />}>{tenantOpsRoutes()}</Route>
        </Route>

        <Route element={<RequireAuth allow={['PLATFORM_ADMIN']} />}>
          <Route element={<PlatformLayout />}>{platformOpsRoutes()}</Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
