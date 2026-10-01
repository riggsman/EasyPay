import { Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { RealtimeProvider } from './contexts/RealtimeContext'
import { PublicLayout, PayerLayout, TenantLayout, PlatformLayout } from './layouts/Layouts'
import LandingPage from './pages/public/LandingPage'
import LoginPage from './pages/public/LoginPage'
import RegisterPage from './pages/public/RegisterPage'
import ForgotPasswordPage from './pages/public/ForgotPasswordPage'
import VerifyPage from './pages/public/VerifyPage'
import PayerDashboard from './pages/payer/Dashboard'
import ObligationsPage from './pages/payer/Obligations'
import MakePaymentPage from './pages/payer/MakePayment'
import PaymentHistory from './pages/payer/PaymentHistory'
import PaymentDetail from './pages/payer/PaymentDetail'
import ReceiptsPage from './pages/payer/Receipts'
import OperatingAreaPage from './pages/payer/OperatingArea'
import ProfilePage from './pages/payer/Profile'
import PayerStatements, { PayerNotifications } from './pages/payer/Statements'
import TenantObligations from './pages/tenant/Obligations'
import TenantRevenue from './pages/tenant/Revenue'
import PlatformTenants from './pages/platform/Tenants'
import PlatformGeography from './pages/platform/Geography'
import PlatformProviders from './pages/platform/Providers'
import {
  OpsDashboard,
  OpsAlerts,
  OpsSearchResults,
  OpsPayers,
  OpsPayerDetail,
  OpsCollections,
  OpsCollectionDetail,
  OpsObligationDetail,
  OpsTransactions,
  OpsTransactionDetail,
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
  OpsSettlementDetail,
  OpsReports,
} from './pages/ops/OpsPages'

function RequireAuth({ allow }) {
  const { isAuthenticated, userType } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (allow && !allow.includes(userType)) {
    if (userType === 'PAYER') return <Navigate to="/payer" replace />
    if (userType === 'PLATFORM_ADMIN' || userType === 'SUPER_ADMIN') return <Navigate to="/platform" replace />
    return <Navigate to="/tenant" replace />
  }
  return <Outlet />
}

function sharedOpsRoutes(prefix) {
  return (
    <>
      <Route path={`${prefix}/alerts`} element={<OpsAlerts />} />
      <Route path={`${prefix}/search`} element={<OpsSearchResults />} />
      <Route path={`${prefix}/users`} element={<OpsUsersRoles />} />
      <Route path={`${prefix}/fees`} element={<OpsFees />} />
      <Route path={`${prefix}/commissions`} element={<OpsCommissions />} />
      <Route path={`${prefix}/config`} element={<OpsConfig />} />
      <Route path={`${prefix}/payers`} element={<OpsPayers />} />
      <Route path={`${prefix}/payers/:id`} element={<OpsPayerDetail />} />
      <Route path={`${prefix}/collections`} element={<OpsCollections />} />
      <Route path={`${prefix}/collections/:id`} element={<OpsCollectionDetail />} />
      <Route path={`${prefix}/transactions`} element={<OpsTransactions />} />
      <Route path={`${prefix}/transactions/:id`} element={<OpsTransactionDetail />} />
      <Route path={`${prefix}/ledger`} element={<OpsLedger />} />
      <Route path={`${prefix}/receipts`} element={<OpsReceipts />} />
      <Route path={`${prefix}/settlements`} element={<OpsSettlements />} />
      <Route path={`${prefix}/settlements/:id`} element={<OpsSettlementDetail />} />
      <Route path={`${prefix}/reconciliation`} element={<OpsReconciliation />} />
      <Route path={`${prefix}/statements`} element={<OpsStatements />} />
      <Route path={`${prefix}/reports`} element={<OpsReports />} />
      <Route path={`${prefix}/audit`} element={<OpsAudit />} />
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <RealtimeProvider>
      <Routes>
        <Route element={<PublicLayout />}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/verify" element={<VerifyPage />} />
          {/* QR deep-link from receipt PDFs — same public verify logic */}
          <Route path="/v/:token" element={<VerifyPage />} />
        </Route>

        <Route element={<RequireAuth allow={['PAYER']} />}>
          <Route element={<PayerLayout />}>
            <Route path="/payer" element={<PayerDashboard />} />
            <Route path="/payer/obligations" element={<ObligationsPage />} />
            <Route path="/payer/pay" element={<MakePaymentPage />} />
            <Route path="/payer/history" element={<PaymentHistory />} />
            <Route path="/payer/payments/:id" element={<PaymentDetail />} />
            <Route path="/payer/receipts" element={<ReceiptsPage />} />
            <Route path="/payer/statements" element={<PayerStatements />} />
            <Route path="/payer/notifications" element={<PayerNotifications />} />
            <Route path="/payer/area" element={<OperatingAreaPage />} />
            <Route path="/payer/profile" element={<ProfilePage />} />
          </Route>
        </Route>

        <Route element={<RequireAuth allow={['STAFF', 'PLATFORM_ADMIN']} />}>
          <Route element={<TenantLayout />}>
            <Route path="/tenant" element={<OpsDashboard mode="tenant" />} />
            <Route path="/tenant/revenue" element={<TenantRevenue />} />
            <Route path="/tenant/obligations" element={<TenantObligations />} />
            <Route path="/tenant/obligations/:id" element={<OpsObligationDetail />} />
            {sharedOpsRoutes('/tenant')}
          </Route>
        </Route>

        <Route element={<RequireAuth allow={['PLATFORM_ADMIN', 'SUPER_ADMIN']} />}>
          <Route element={<PlatformLayout />}>
            <Route path="/platform" element={<OpsDashboard mode="platform" />} />
            <Route path="/platform/tenants" element={<PlatformTenants />} />
            <Route path="/platform/geography" element={<PlatformGeography />} />
            <Route path="/platform/providers" element={<PlatformProviders />} />
            <Route path="/platform/obligations" element={<TenantObligations />} />
            {sharedOpsRoutes('/platform')}
          </Route>
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      </RealtimeProvider>
    </AuthProvider>
  )
}
