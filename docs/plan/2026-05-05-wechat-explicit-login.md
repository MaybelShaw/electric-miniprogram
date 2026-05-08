# 微信快捷登录与分享回跳实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 取消隐式创建账号，改为显式微信快捷登录、手机号授权和登录后回跳。

**Architecture:** 后端新增显式登录接口，前端通过动作守卫拦截交易动作。分享商品页允许游客浏览，购买动作触发登录，登录完成后恢复原路径和原动作。

**Tech Stack:** Django 5.2、DRF、SimpleJWT、Taro 4、微信小程序登录与手机号授权。

---

## 影响范围

- 修改：`backend/users/views.py`
- 修改：`backend/users/serializers.py`
- 修改：`backend/users/urls.py`
- 修改：`backend/users/models.py`
- 新增：`backend/users/tests/test_wechat_explicit_login.py`
- 修改：`frontend/src/services/auth.ts`
- 修改：`frontend/src/utils/auth-guard.ts`
- 修改：`frontend/src/pages/product-detail/index.tsx`
- 修改：`frontend/src/pages/profile/index.tsx`
- 修改：`docs/frontend.md`、`docs/backend.md`

## 执行步骤

- [x] 写失败测试：首次微信快捷登录缺少手机号授权时拒绝创建用户。
- [x] 写失败测试：带手机号授权时创建或复用用户，返回 access/refresh token。
- [x] 写失败测试：默认昵称生成且不要求用户首次填写头像昵称。
- [x] 新增后端登录接口，入参包含 `code` 和手机号授权凭证。
- [x] 后端封装微信 code 换 openid/session_key 的服务，测试中 mock 外部请求。
- [x] 后端保存手机号和登录时间。
- [x] 前端新增显式登录服务，不再在普通浏览时隐式创建账号。
- [x] 前端新增交易动作守卫，未登录时记录原路径和待恢复动作。
- [x] 商品分享页允许未登录浏览详情。
- [x] 点击立即购买时触发登录，登录后回到原商品详情并继续购买动作。

## 验证命令

- [ ] `cd backend && .\.venv\Scripts\python.exe manage.py test users.tests.test_wechat_explicit_login`
- [x] `cd frontend && npm run build:weapp`
- [ ] 微信开发者工具手测：分享商品页游客可浏览，购买触发登录，登录后回跳。

## 完成标准

- 首次登录必须拿到手机号。
- 未登录用户能浏览分享商品详情。
- 未登录购买动作会进入登录流程。
- 登录后回到原商品并继续购买。
- 测试和构建通过后，本计划可单独提交并归档。
