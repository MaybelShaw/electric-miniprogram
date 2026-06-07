import { Layout as AntLayout, Menu, Button, Badge, Select, notification } from 'antd';
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
  AppstoreAddOutlined,
  CustomerServiceOutlined,
  BookOutlined,
  PartitionOutlined,
  ShopOutlined,
  TeamOutlined,
  DatabaseOutlined,
  FileSearchOutlined,
  HistoryOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';
import { useEffect, useState, useRef } from 'react';
import { removeToken } from '@/utils/auth';
import { getCurrentStoreContext, getFeedbackTicketStats, getSupportTickets } from '@/services/api';
import type { CurrentStoreContext } from '@/services/types';
import { canAccessAdminRoute, STORE_DEFAULT_ROUTE } from '@/utils/permissions';
import { getSelectedStoreId, setSelectedStoreId } from '@/utils/store';
import './index.css';

const { Header, Sider, Content, Footer } = AntLayout;

export const adminMenuItems = [
  { key: '/admin/feedback-tickets', icon: <CustomerServiceOutlined />, label: '问题建议' },
  {
    key: '/admin/platform-group',
    icon: <UserOutlined />,
    label: '平台管理',
    children: [
      { key: '/admin/users', icon: <UserOutlined />, label: '用户管理' },
      { key: '/admin/stores', icon: <ShopOutlined />, label: '店铺管理' },
      { key: '/admin/store-members', icon: <TeamOutlined />, label: '店铺成员' },
      { key: '/admin/user-stats', icon: <BarChartOutlined />, label: '用户统计' },
      { key: '/admin/company-certification', icon: <SafetyCertificateOutlined />, label: '认证审核' },
    ],
  },
  {
    key: '/admin/operation-group',
    icon: <AppstoreOutlined />,
    label: '运营管理',
    children: [
      { key: '/admin/sales-stats', icon: <RiseOutlined />, label: '销售统计' },
      { key: '/admin/home-banners', icon: <PictureOutlined />, label: '轮播图管理' },
      { key: '/admin/special-zones', icon: <PartitionOutlined />, label: '活动管理' },
      { key: '/admin/home-store-cards', icon: <AppstoreAddOutlined />, label: '首页卡片管理' },
      { key: '/admin/cases', icon: <BookOutlined />, label: '案例管理' },
      { key: '/admin/brands', icon: <TagOutlined />, label: '品牌管理' },
      { key: '/admin/categories', icon: <AppstoreOutlined />, label: '分类管理' },
      { key: '/admin/products', icon: <ShoppingOutlined />, label: '产品管理' },
      { key: '/admin/product-skus', icon: <DatabaseOutlined />, label: 'SKU管理' },
      { key: '/admin/customer-groups', icon: <TeamOutlined />, label: '客户分组' },
      { key: '/admin/media-images', icon: <PictureOutlined />, label: '媒体库' },
      { key: '/admin/search-logs', icon: <FileSearchOutlined />, label: '搜索日志' },
      { key: '/admin/inventory-logs', icon: <HistoryOutlined />, label: '库存日志' },
    ],
  },
  {
    key: '/admin/finance-group',
    icon: <AccountBookOutlined />,
    label: '账务管理',
    children: [
      { key: '/admin/credit-accounts', icon: <CreditCardOutlined />, label: '信用账户' },
      { key: '/admin/account-statements', icon: <AccountBookOutlined />, label: '对账单' },
      { key: '/admin/account-transactions', icon: <AccountBookOutlined />, label: '交易记录' },
    ],
  },
  {
    key: '/admin/order-group',
    icon: <ShoppingCartOutlined />,
    label: '订单辅助',
    children: [
      { key: '/admin/orders', icon: <ShoppingCartOutlined />, label: '订单管理' },
      { key: '/admin/invoices', icon: <FileTextOutlined />, label: '发票管理' },
      { key: '/admin/discounts', icon: <PercentageOutlined />, label: '折扣管理' },
    ],
  },
];

export const supportMenuItems = [
  { key: '/support/orders', icon: <ShoppingCartOutlined />, label: '订单管理' },
  { key: '/support/invoices', icon: <FileTextOutlined />, label: '发票管理' },
  { key: '/support/tickets', icon: <CustomerServiceOutlined />, label: '消息' },
  { key: '/support/feedback-tickets', icon: <CustomerServiceOutlined />, label: '问题建议' },
  { key: '/support/templates', icon: <BookOutlined />, label: '模板管理' },
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
  const [feedbackPendingCount, setFeedbackPendingCount] = useState(0);
  const [storeContext, setStoreContext] = useState<CurrentStoreContext | null>(null);
  const [selectedStoreId, setSelectedStoreIdState] = useState<number | null>(getSelectedStoreId());
  const lastCountRef = useRef<number | null>(null);

  const isSupportLayout = title === '客服系统' || menuItems.some(item => item.key === '/support/tickets');

  useEffect(() => {
    if (isSupportLayout) return;

    getCurrentStoreContext()
      .then((context) => {
        setStoreContext(context);
        const availableIds = new Set(context.stores.map(store => store.id));
        const fallbackStoreId = context.default_store?.id || context.stores[0]?.id || null;
        if ((!selectedStoreId || !availableIds.has(selectedStoreId)) && fallbackStoreId) {
          setSelectedStoreId(fallbackStoreId);
          setSelectedStoreIdState(fallbackStoreId);
        }
      })
      .catch(() => {
        setStoreContext(null);
      });
  }, [isSupportLayout, selectedStoreId]);

  useEffect(() => {
    if (isSupportLayout || !storeContext || storeContext.is_platform_admin) return;
    if (!canAccessAdminRoute(location.pathname, storeContext)) {
      navigate(STORE_DEFAULT_ROUTE, { replace: true });
    }
  }, [isSupportLayout, location.pathname, navigate, storeContext]);

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
            description: `您有 ${count} 条待处理消息`,
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

  useEffect(() => {
    const pollFeedback = async () => {
      try {
        const res: any = await getFeedbackTicketStats();
        setFeedbackPendingCount(res.pending_count || 0);
      } catch (e) {
        setFeedbackPendingCount(0);
      }
    };

    pollFeedback();
    const intervalId = setInterval(pollFeedback, 10000);
    return () => clearInterval(intervalId);
  }, []);

  const handleLogout = () => {
    removeToken();
    navigate('/login');
  };

  const visibleMenuItems = !isSupportLayout && !storeContext
    ? []
    : storeContext && !storeContext.is_platform_admin
      ? menuItems
        .map(item => {
          if (!item.children) return canAccessAdminRoute(item.key, storeContext) ? item : null;
          const children = item.children.filter((child: any) => canAccessAdminRoute(child.key, storeContext));
          return children.length > 0 ? { ...item, children } : null;
        })
        .filter(Boolean)
      : menuItems;
  const currentStore = storeContext?.stores.find(store => store.id === selectedStoreId) || storeContext?.default_store || storeContext?.stores[0];

  const itemsWithBadge = visibleMenuItems.map(item => {
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
    if ((item.key === '/admin/feedback-tickets' || item.key === '/support/feedback-tickets') && feedbackPendingCount > 0) {
      return {
        ...item,
        label: (
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>{item.label}</span>
            <Badge count={feedbackPendingCount} size="small" style={{ marginLeft: 8 }} />
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
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'flex-end', gap: 12 }}>
          {storeContext && !storeContext.is_platform_admin && currentStore && (
            <span style={{ color: '#666' }}>当前店铺：{currentStore.name}</span>
          )}
          {storeContext?.is_platform_admin && storeContext.stores.length > 0 && (
            <Select
              style={{ width: 180 }}
              value={selectedStoreId || storeContext.default_store?.id}
              options={storeContext.stores.map(store => ({ label: store.name, value: store.id }))}
              onChange={(storeId) => {
                setSelectedStoreId(storeId);
                setSelectedStoreIdState(storeId);
                window.location.reload();
              }}
            />
          )}
          <Button icon={<LogoutOutlined />} onClick={handleLogout}>
            退出登录
          </Button>
        </Header>
        <Content style={{ margin: '24px', background: '#fff', padding: 24, minHeight: 280 }}>
          {children}
        </Content>
        <Footer className="footer">
          <a href="https://beian.miit.gov.cn/" target="_blank" rel="noreferrer">
            皖ICP备2025107960号-1
          </a>
        </Footer>
      </AntLayout>
    </AntLayout>
  );
}
