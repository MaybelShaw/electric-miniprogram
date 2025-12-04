import { Layout as AntLayout, Menu, Button, Badge, notification } from 'antd';
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
  RiseOutlined,
  PictureOutlined,
  CustomerServiceOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useEffect, useState, useRef } from 'react';
import { removeToken } from '@/utils/auth';
import { getSupportTickets } from '@/services/api';
import './index.css';

const { Header, Sider, Content } = AntLayout;

export const adminMenuItems = [
  { key: '/admin/users', icon: <UserOutlined />, label: '用户管理' },
  { key: '/admin/user-stats', icon: <BarChartOutlined />, label: '用户统计' },
  { key: '/admin/sales-stats', icon: <RiseOutlined />, label: '销售统计' },
  { key: '/admin/company-certification', icon: <SafetyCertificateOutlined />, label: '认证审核' },
  { key: '/admin/credit-accounts', icon: <CreditCardOutlined />, label: '信用账户' },
  { key: '/admin/account-statements', icon: <AccountBookOutlined />, label: '对账单' },
  { key: '/admin/account-transactions', icon: <AccountBookOutlined />, label: '交易记录' },
  { key: '/admin/home-banners', icon: <PictureOutlined />, label: '轮播图管理' },
  { key: '/admin/brands', icon: <TagOutlined />, label: '品牌管理' },
  { key: '/admin/categories', icon: <AppstoreOutlined />, label: '分类管理' },
  { key: '/admin/products', icon: <ShoppingOutlined />, label: '产品管理' },
  { key: '/admin/orders', icon: <ShoppingCartOutlined />, label: '订单管理' },
  { key: '/admin/invoices', icon: <FileTextOutlined />, label: '发票管理' },
  { key: '/admin/discounts', icon: <PercentageOutlined />, label: '折扣管理' },
];

export const supportMenuItems = [
  { key: '/support/orders', icon: <ShoppingCartOutlined />, label: '订单管理' },
  { key: '/support/invoices', icon: <FileTextOutlined />, label: '发票管理' },
  { key: '/support/tickets', icon: <CustomerServiceOutlined />, label: '工单与消息' },
];

interface LayoutProps {
  children: React.ReactNode;
  menuItems?: any[];
  title?: string;
}

export default function Layout({ children, menuItems = adminMenuItems, title = '商户管理' }: LayoutProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const [unreadCount, setUnreadCount] = useState(0);
  const lastCountRef = useRef<number | null>(null);

  const isSupportLayout = title === '客服系统' || menuItems.some(item => item.key === '/support/tickets');

  useEffect(() => {
    if (!isSupportLayout) return;

    const pollTickets = async () => {
      try {
        // Get open tickets count
        const res: any = await getSupportTickets({ status: 'open', page_size: 1 });
        const count = res.count || res.total || 0;

        if (lastCountRef.current !== null && count > lastCountRef.current) {
          notification.info({
            message: '新消息提醒',
            description: `您有 ${count} 条待处理工单`,
            placement: 'bottomRight',
            onClick: () => {
              navigate('/support/tickets');
            }
          });
        }
        
        lastCountRef.current = count;
        setUnreadCount(count);
      } catch (e) {
        console.error('Polling tickets failed', e);
      }
    };

    pollTickets();
    const intervalId = setInterval(pollTickets, 5000); // Poll every 5 seconds

    return () => clearInterval(intervalId);
  }, [isSupportLayout, navigate]);

  const handleLogout = () => {
    removeToken();
    navigate('/login');
  };

  const itemsWithBadge = menuItems.map(item => {
    if (item.key === '/support/tickets' && unreadCount > 0) {
      return {
        ...item,
        label: (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>{item.label}</span>
            <Badge count={unreadCount} size="small" style={{ marginLeft: 8 }} />
          </div>
        )
      };
    }
    return item;
  });

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider width={200}>
        <div className="logo">{title}</div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={itemsWithBadge}
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
