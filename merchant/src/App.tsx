import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Layout, { adminMenuItems, supportMenuItems } from './components/Layout';
import RoleGuard from './components/RoleGuard';
import Users from './pages/Users';
import UserStats from './pages/UserStats';
import SalesStats from './pages/SalesStats';
import Stores from './pages/Stores';
import StoreMembers from './pages/StoreMembers';
import CustomerGroups from './pages/CustomerGroups';
import Brands from './pages/Brands';
import Categories from './pages/Categories';
import Products from './pages/Products';
import ProductSKUs from './pages/ProductSKUs';
import MediaImages from './pages/MediaImages';
import SearchLogs from './pages/SearchLogs';
import InventoryLogs from './pages/InventoryLogs';
import Orders from './pages/Orders';
import Invoices from './pages/Invoices';
import Discounts from './pages/Discounts';
import CompanyCertification from './pages/CompanyCertification';
import CreditAccounts from './pages/CreditAccounts';
import AccountStatements from './pages/AccountStatements';
import AccountTransactions from './pages/AccountTransactions';
import ProfitSharing from './pages/ProfitSharing';
import HomeBanners from './pages/HomeBanners';
import HomeStoreCards from './pages/HomeStoreCards';
import SpecialZones from './pages/SpecialZones';
import SpecialZoneCovers from './pages/SpecialZoneCovers';
import Cases from './pages/Cases';
import Support from './pages/Support';
import FeedbackTickets from './pages/FeedbackTickets';
import { getUser } from './utils/auth';
import { isPlatformUserFromStoredUser, isStoreBackendUser, PLATFORM_DEFAULT_ROUTE, STORE_DEFAULT_ROUTE } from './utils/permissions';

const RootRedirect = () => {
  const user = getUser();
  if (!user) return <Navigate to="/admin/login" replace />;
  
  if (user.role === 'support') {
    return <Navigate to="/support" replace />;
  }
  return <Navigate to="/admin" replace />;
};

const AdminDefaultRedirect = () => {
  const user = getUser();
  if (!user) return <Navigate to="/admin/login" replace />;
  if (isStoreBackendUser(user) && !isPlatformUserFromStoredUser(user)) {
    return <Navigate to={STORE_DEFAULT_ROUTE.replace('/admin/', '')} replace />;
  }
  return <Navigate to={PLATFORM_DEFAULT_ROUTE.replace('/admin/', '')} replace />;
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Login Routes */}
        <Route path="/admin/login" element={<Login role="admin" />} />
        <Route path="/support/login" element={<Login role="support" />} />
        <Route path="/login" element={<Navigate to="/admin/login" replace />} />
        
        {/* Admin Routes */}
        <Route
          path="/admin/*"
          element={
            <RoleGuard allowedRoles={['admin']}>
              <Layout menuItems={adminMenuItems} title="商户管理">
                <Routes>
                  <Route path="/" element={<AdminDefaultRedirect />} />
                  <Route path="users" element={<Users />} />
                  <Route path="user-stats" element={<UserStats />} />
                  <Route path="sales-stats" element={<SalesStats />} />
                  <Route path="stores" element={<Stores />} />
                  <Route path="store-members" element={<StoreMembers />} />
                  <Route path="customer-groups" element={<CustomerGroups />} />
                  <Route path="brands" element={<Brands />} />
                  <Route path="categories" element={<Categories />} />
                  <Route path="products" element={<Products />} />
                  <Route path="product-skus" element={<ProductSKUs />} />
                  <Route path="media-images" element={<MediaImages />} />
                  <Route path="search-logs" element={<SearchLogs />} />
                  <Route path="inventory-logs" element={<InventoryLogs />} />
                  <Route path="orders" element={<Orders />} />
                  <Route path="invoices" element={<Invoices />} />
                  <Route path="discounts" element={<Discounts />} />
                  <Route path="company-certification" element={<CompanyCertification />} />
                  <Route path="credit-accounts" element={<CreditAccounts />} />
                  <Route path="account-statements" element={<AccountStatements />} />
                  <Route path="account-transactions" element={<AccountTransactions />} />
                  <Route path="profit-sharing" element={<ProfitSharing />} />
                  <Route path="home-banners" element={<HomeBanners />} />
                  <Route path="home-store-cards" element={<HomeStoreCards />} />
                  <Route path="special-zones" element={<SpecialZones />} />
                  <Route path="special-zone-covers" element={<SpecialZoneCovers />} />
                  <Route path="cases" element={<Cases />} />
                  <Route path="feedback-tickets" element={<FeedbackTickets />} />
                </Routes>
              </Layout>
            </RoleGuard>
          }
        />

        {/* Support Routes */}
        <Route
          path="/support/*"
          element={
            <RoleGuard allowedRoles={['support']}>
              <Layout menuItems={supportMenuItems} title="客服系统">
                <Routes>
                  <Route path="/" element={<Navigate to="tickets" replace />} />
                  <Route path="orders" element={<Orders />} />
                  <Route path="invoices" element={<Invoices />} />
                  <Route path="tickets" element={<Support />} />
                  <Route path="feedback-tickets" element={<FeedbackTickets />} />
                  <Route path="templates" element={<Support />} />
                </Routes>
              </Layout>
            </RoleGuard>
          }
        />

        {/* Root Redirect */}
        <Route path="/" element={<RootRedirect />} />
        
        {/* Catch all - redirect to root to handle logic */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
