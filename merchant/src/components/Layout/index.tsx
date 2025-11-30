import { Layout as AntLayout, Menu, Button } from 'antd';
import {
  UserOutlined,
  TagOutlined,
  AppstoreOutlined,
  ShoppingOutlined,
  ShoppingCartOutlined,
  PercentageOutlined,
  SafetyCertificateOutlined,
  AccountBookOutlined,
  CreditCardOutlined,
  LogoutOutlined,
  FileTextOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { removeToken } from '@/utils/auth';
import './index.css';

const { Header, Sider, Content } = AntLayout;

const menuItems = [
  { key: '/users', icon: <UserOutlined />, label: '用户管理' },
  { key: '/user-stats', icon: <BarChartOutlined />, label: '用户统计' },
  { key: '/company-certification', icon: <SafetyCertificateOutlined />, label: '认证审核' },
  { key: '/credit-accounts', icon: <CreditCardOutlined />, label: '信用账户' },
  { key: '/account-statements', icon: <AccountBookOutlined />, label: '对账单' },
  { key: '/account-transactions', icon: <AccountBookOutlined />, label: '交易记录' },
  { key: '/brands', icon: <TagOutlined />, label: '品牌管理' },
  { key: '/categories', icon: <AppstoreOutlined />, label: '品类管理' },
  { key: '/products', icon: <ShoppingOutlined />, label: '产品管理' },
  { key: '/orders', icon: <ShoppingCartOutlined />, label: '订单管理' },
  { key: '/invoices', icon: <FileTextOutlined />, label: '发票管理' },
  { key: '/discounts', icon: <PercentageOutlined />, label: '折扣管理' },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    removeToken();
    navigate('/login');
  };

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider width={200}>
        <div className="logo">商户管理</div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <AntLayout>
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'flex-end' }}>
          <Button icon={<LogoutOutlined />} onClick={handleLogout}>
            退出登录
          </Button>
        </Header>
        <Content style={{ margin: '24px', background: '#fff', padding: 24, minHeight: 280 }}>
          {children}
        </Content>
      </AntLayout>
    </AntLayout>
  );
}
