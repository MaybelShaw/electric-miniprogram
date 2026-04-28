# 前端 ESLint Error 清理（仅 error）设计

- 日期：2026-04-28
- 状态：Draft（已确认）
- 范围：`frontend/src/pages/order-detail/index.tsx`、`frontend/src/pages/product-detail/index.tsx`

## 1. 背景

当前前端存在历史 ESLint 问题，集中在订单详情与商品详情两个大文件。为避免和业务功能改动混在一起，本次仅做 lint error 清理，不处理 warning。

## 2. 目标与非目标

### 2.1 目标

1. 清理指定两个文件中的 ESLint `error`。
2. 保持业务行为不变。
3. 输出单独 commit，便于审查与回滚。

### 2.2 非目标

1. 不处理 `warning`（包含 `react-hooks/exhaustive-deps`）。
2. 不扩大到其他页面。
3. 不做逻辑重构或功能改造。

## 3. 范围与问题类型

已确认问题类型：

1. `@typescript-eslint/no-shadow`
2. `react/jsx-closing-bracket-location`
3. `react/jsx-indent-props`
4. `jsx-quotes`

## 4. 实施策略

1. 仅修改两个目标文件。
2. 以最小改动修复 error：
   - 变量重名 -> 局部改名
   - JSX 引号/缩进/闭合位置 -> 按规则调整格式
3. 不触碰 warning 对应代码。
4. 每次修复后运行定向 eslint 校验。

## 5. 验收标准

执行：

```bash
cd frontend
npx eslint src/pages/order-detail/index.tsx src/pages/product-detail/index.tsx
```

验收：

1. `error = 0`
2. `warning` 可保留
3. 页面功能路径不受影响（至少基础手工冒烟）

## 6. 风险与控制

1. 风险：格式改动触发大 diff
   - 控制：仅针对报错行最小修改，不整文件格式化。
2. 风险：重命名变量引入引用遗漏
   - 控制：修改后定向 lint + 基础运行冒烟。

## 7. 交付

1. 单独提交 lint cleanup commit。
2. 提交信息：`chore: 清理订单详情与商品详情页面eslint错误`。

## 8. 结论

本次以最小风险清理历史 `error`，提升代码基线质量，同时避免与功能需求耦合。
