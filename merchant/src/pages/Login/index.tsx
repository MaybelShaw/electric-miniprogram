import { Form, Input, Button, Card, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { loginAdmin, loginSupport } from '@/services/api';
import { setToken, setUser } from '@/utils/auth';
import './index.css';

export default function Login({ role = 'admin' }: { role?: 'admin' | 'support' }) {
  const navigate = useNavigate();

  const onFinish = async (values: any) => {
    try {
      const res: any = role === 'support' ? await loginSupport(values) : await loginAdmin(values);
      
      // Check if user role matches the login page role
      if (role === 'support' && res.user.role !== 'support') {
        message.error('非客服账号请前往管理员登录页面');
        return;
      }
      
      if (role === 'admin' && res.user.role === 'support') {
        message.error('客服账号请前往客服登录页面');
        return;
      }

      setToken(res.access);
      setUser(res.user);
      message.success('登录成功');
      
      if (res.user.role === 'support') {
        navigate('/support');
      } else {
        navigate('/admin');
      }
    } catch (error) {
      message.error('登录失败');
    }
  };

  return (
    <div className="login-container">
      <Card title={role === 'support' ? "客服系统登录" : "商户管理后台"} className="login-card">
        <Form onFinish={onFinish} autoComplete="off">
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" size="large" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" size="large" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block size="large">
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
