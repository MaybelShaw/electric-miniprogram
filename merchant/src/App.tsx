import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Layout from './components/Layout';
import Users from './pages/Users';
import Brands from './pages/Brands';
import Categories from './pages/Categories';
import Products from './pages/Products';
import Orders from './pages/Orders';
import Discounts from './pages/Discounts';
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
                  <Route path="/discounts" element={<Discounts />} />
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
