import axios from 'axios';
import { message } from 'antd';
import { getToken, removeToken } from './auth';

const request = axios.create({
  baseURL: '/api',
  timeout: 10000,
});

export async function fetchAllPaginated<T extends { id: number }>(
  fetcher: (params?: any) => Promise<any>,
  baseParams: Record<string, any> = {},
  preferredPageSize = 100,
): Promise<T[]> {
  const firstRes: any = await fetcher({ ...baseParams, page: 1, page_size: preferredPageSize });
  if (Array.isArray(firstRes)) return firstRes as T[];

  const firstPage: T[] = (firstRes?.results || []) as T[];
  const itemsById = new Map<number, T>();
  for (const item of firstPage) {
    if (item && typeof item.id === 'number') itemsById.set(item.id, item);
  }

  const totalPages = Number(firstRes?.total_pages);
  const hasNextFromFirst = typeof firstRes?.has_next === 'boolean' ? firstRes.has_next : Boolean(firstRes?.next);
  if (!hasNextFromFirst && (!Number.isFinite(totalPages) || totalPages <= 1)) {
    return Array.from(itemsById.values());
  }

  const maxPages = Number.isFinite(totalPages) && totalPages > 0 ? Math.min(totalPages, 200) : 200;
  for (let page = 2; page <= maxPages; page += 1) {
    const res: any = await fetcher({ ...baseParams, page, page_size: preferredPageSize });
    if (Array.isArray(res)) {
      for (const item of res as T[]) {
        if (item && typeof item.id === 'number') itemsById.set(item.id, item);
      }
      break;
    }

    const pageItems: T[] = (res?.results || []) as T[];
    for (const item of pageItems) {
      if (item && typeof item.id === 'number') itemsById.set(item.id, item);
    }

    const hasNext = typeof res?.has_next === 'boolean' ? res.has_next : Boolean(res?.next);
    const pageTotalPages = Number(res?.total_pages);
    if (!hasNext && (!Number.isFinite(pageTotalPages) || page >= pageTotalPages)) break;
  }

  return Array.from(itemsById.values());
}

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
