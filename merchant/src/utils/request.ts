import axios from 'axios';
import { message } from 'antd';
import { getToken, removeToken } from './auth';

const request = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

request.interceptors.request.use(
  (config) => {
    const token = getToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      message.error('登录已过期，请重新登录');
      removeToken();
      // Redirect based on current path to keep context
      if (window.location.pathname.startsWith('/support')) {
        window.location.href = '/support/login';
      } else {
        window.location.href = '/admin/login';
      }
    } else {
      message.error(error.response?.data?.message || '请求失败');
    }
    return Promise.reject(error);
  }
);

export default request;
