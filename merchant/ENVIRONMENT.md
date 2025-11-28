## 环境变量统一说明（merchant 管理端）

### 1. Vite / 运行时环境

- 使用 Vite 默认的 `.env.*` 机制：
  - 开发环境：`.env.development`
  - 生产环境：`.env.production`

### 2. 统一的后台地址参数

- **变量名**：`VITE_BACKEND_ORIGIN`
- **作用**：指定后端 Django 服务的 Origin（协议 + 域名 + 端口），例如：
  - 开发：`VITE_BACKEND_ORIGIN=http://127.0.0.1:8000`
  - 生产：`VITE_BACKEND_ORIGIN=https://api.example.com`

### 3. 生效位置

- `vite.config.ts` 中使用：

```ts
// 只展示关键片段
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiTarget = env.VITE_BACKEND_ORIGIN || 'http://127.0.0.1:8000';

  return {
    server: {
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
  };
});
```

前端业务代码统一使用 `axios` 的 `baseURL: '/api'`，因此只需要修改 `.env.*` 中的 `VITE_BACKEND_ORIGIN` 即可切换后端环境。


