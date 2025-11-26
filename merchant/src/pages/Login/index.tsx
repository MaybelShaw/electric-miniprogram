import { Form, Input, Button, Card, message } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { login } from '@/services/api';
import { setToken } from '@/utils/auth';
import './index.css';

export default function Login() {
  const navigate = useNavigate();

  const onFinish = async (values: any) => {
    try {
      const res: any = await login(values);
      setToken(res.access);
      message.success('登录成功');
      navigate('/');
    } catch (error) {
      message.error('登录失败');
    }
  };

  return (
    <div className="login-container">
      <Card title="商户管理后台" className="login-card">
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
