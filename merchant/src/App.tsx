import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Layout from './components/Layout';
import Users from './pages/Users';
import Brands from './pages/Brands';
import Categories from './pages/Categories';
import Products from './pages/Products';
import Orders from './pages/Orders';
import Invoices from './pages/Invoices';
import Discounts from './pages/Discounts';
import CompanyCertification from './pages/CompanyCertification';
import CreditAccounts from './pages/CreditAccounts';
import AccountStatements from './pages/AccountStatements';
import AccountTransactions from './pages/AccountTransactions';
import { getToken } from './utils/auth';

const PrivateRoute = ({ children }: { children: React.ReactNode }) => {
  return getToken() ? <>{children}</> : <Navigate to="/login" replace />;
};

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <PrivateRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<Navigate to="/users" replace />} />
                  <Route path="/users" element={<Users />} />
                  <Route path="/brands" element={<Brands />} />
                  <Route path="/categories" element={<Categories />} />
                  <Route path="/products" element={<Products />} />
                  <Route path="/orders" element={<Orders />} />
                  <Route path="/invoices" element={<Invoices />} />
                  <Route path="/discounts" element={<Discounts />} />
                  <Route path="/company-certification" element={<CompanyCertification />} />
                  <Route path="/credit-accounts" element={<CreditAccounts />} />
                  <Route path="/account-statements" element={<AccountStatements />} />
                  <Route path="/account-transactions" element={<AccountTransactions />} />
                </Routes>
              </Layout>
            </PrivateRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
