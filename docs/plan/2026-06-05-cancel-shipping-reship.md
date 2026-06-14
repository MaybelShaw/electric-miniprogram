# 取消发货与受控重新发货 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 Merchant 增加一次性取消发货能力，并复用现有发货接口安全完成本地或微信重新发货，同时保留管理员可审计的完整发货操作记录。

**Architecture:** 新增 `OrderShippingAction` 作为发货、取消发货、重新发货的审计记录，由独立领域服务统一处理海尔识别、能力判断、物流快照和取消事务。现有 `/ship/` 保持为唯一发货入口，但根据成功取消记录识别重新发货；需要微信同步的重新发货必须同步成功后才提交本地状态，失败时回滚并在独立事务中记录失败尝试。Merchant 只消费后端能力字段，不自行推断海尔、支付方式或微信同步规则。

**Tech Stack:** Django 5.2, Django REST Framework, PostgreSQL/SQLite tests, Python 3.12, React 18, TypeScript, Ant Design Pro, Vite, uv.

---

## File Map

- Create: `backend/orders/shipping_action_service.py`
  - 统一海尔订单识别、物流快照、取消资格、重新发货上下文和审计记录写入。
- Create: `backend/orders/tests/test_shipping_actions.py`
  - 覆盖模型约束、取消接口、能力字段、微信重发回滚和旧订单兼容。
- Create: `backend/orders/migrations/0028_ordershippingaction.py`
  - 新增操作记录表和“每单最多一次成功取消发货”条件唯一约束。
- Modify: `backend/orders/models.py`
  - 新增 `OrderShippingAction`。
- Modify: `backend/orders/admin.py`
  - 注册发货操作记录，便于后台审计。
- Modify: `backend/orders/state_machine.py`
  - 增加仅供取消发货领域服务调用的 `shipped -> paid` 受控回退方法。
- Modify: `backend/orders/serializers.py`
  - 增加能力字段和管理员操作记录序列化器，复用统一海尔识别。
- Modify: `backend/orders/views.py`
  - 增加取消发货、发货记录接口，并将现有发货流程接入 `ship/reship` 审计。
- Verify: `backend/orders/wechat_shipping_service.py`
  - 保留现有 `10060023` 幂等成功语义，并用测试锁定行为。
- Modify: `merchant/src/services/types.ts`
  - 增加订单能力字段、完整物流信息和发货操作记录类型。
- Modify: `merchant/src/services/api.ts`
  - 增加取消发货和查询发货操作记录 API。
- Modify: `merchant/src/pages/Orders/index.tsx`
  - 增加取消发货弹窗、重新发货提示和详情历史记录。
- Modify: `docs/api/api.md`
  - 记录两个新接口和订单能力字段。
- Move after completion: `docs/plan/2026-06-05-cancel-shipping-reship.md` -> `docs/plan/archive/2026-06-05-cancel-shipping-reship.md`
  - 代码、测试和提交完成后归档计划。

### Task 1: 新增发货操作记录模型与数据库约束

**Files:**
- Modify: `backend/orders/models.py`
- Create: `backend/orders/migrations/0028_ordershippingaction.py`
- Modify: `backend/orders/admin.py`
- Create: `backend/orders/tests/test_shipping_actions.py`

- [ ] **Step 1: 写模型约束失败测试**

```python
# backend/orders/tests/test_shipping_actions.py
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase

from catalog.models import Product
from orders.models import Order, OrderShippingAction


class ShippingFixtureMixin:
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='shipping-buyer',
            password='pwd',
        )
        self.operator = get_user_model().objects.create_user(
            username='shipping-admin',
            password='pwd',
            is_staff=True,
        )
        self.product = Product.objects.create(
            name='本地测试商品',
            price=Decimal('100.00'),
            stock=10,
            source='local',
        )
        self.order = Order.objects.create(
            user=self.user,
            product=self.product,
            quantity=1,
            total_amount=Decimal('100.00'),
            actual_amount=Decimal('100.00'),
            status='shipped',
        )
        self.order.logistics_no = 'KY4001016483553'
        self.order.delivery_record_code = 'DELIVERY-1'
        self.order.sn_code = 'SN-1'
        self.order.shipping_info = {
            'logistics_type': 1,
            'delivery_mode': 1,
            'shipping_list': [{
                'express_company': 'KYSY',
                'tracking_no': 'KY4001016483553',
                'item_desc': '测试商品*1',
            }],
        }
        self.order.delivery_images = ['https://cdn.example.com/delivery.jpg']
        self.order.save()


class ShippingActionModelTests(ShippingFixtureMixin, TestCase):

    def test_only_one_successful_cancel_shipping_action_is_allowed(self):
        OrderShippingAction.objects.create(
            order=self.order,
            action='cancel_shipping',
            status='succeeded',
            operator=self.operator,
            reason='第一次取消',
            shipping_snapshot={'logistics_no': 'SF001'},
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                OrderShippingAction.objects.create(
                    order=self.order,
                    action='cancel_shipping',
                    status='succeeded',
                    operator=self.operator,
                    reason='第二次取消',
                    shipping_snapshot={'logistics_no': 'SF002'},
                )

    def test_failed_cancel_does_not_consume_successful_cancel_slot(self):
        OrderShippingAction.objects.create(
            order=self.order,
            action='cancel_shipping',
            status='failed',
            operator=self.operator,
            reason='失败尝试',
        )
        action = OrderShippingAction.objects.create(
            order=self.order,
            action='cancel_shipping',
            status='succeeded',
            operator=self.operator,
            reason='成功取消',
        )
        self.assertEqual(action.status, 'succeeded')
```

- [ ] **Step 2: 运行测试确认模型不存在**

Run:

```bash
cd backend
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py test orders.tests.test_shipping_actions.ShippingActionModelTests -v 2
```

Expected: FAIL，导入 `OrderShippingAction` 失败。

- [ ] **Step 3: 新增模型**

在 `backend/orders/models.py` 的 `OrderShippingSync` 前新增：

```python
class OrderShippingAction(models.Model):
    """管理员发货操作审计记录。"""

    ACTION_CHOICES = [
        ('ship', '发货'),
        ('cancel_shipping', '取消发货'),
        ('reship', '重新发货'),
    ]
    STATUS_CHOICES = [
        ('succeeded', '成功'),
        ('failed', '失败'),
    ]

    id = models.BigAutoField(primary_key=True)
    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name='shipping_actions',
        verbose_name='订单',
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, verbose_name='操作')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name='结果')
    shipping_snapshot = models.JSONField(default=dict, blank=True, verbose_name='物流快照')
    operator = models.ForeignKey(
        'users.User',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='shipping_actions',
        verbose_name='操作人',
    )
    reason = models.CharField(max_length=200, blank=True, default='', verbose_name='原因')
    wechat_sync_required = models.BooleanField(default=False, verbose_name='需要同步微信')
    wechat_synced = models.BooleanField(default=False, verbose_name='微信同步成功')
    wechat_response = models.JSONField(default=dict, blank=True, verbose_name='微信响应摘要')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        verbose_name = '发货操作记录'
        verbose_name_plural = '发货操作记录'
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['order', 'created_at'], name='orders_ship_action_order_idx'),
            models.Index(fields=['action', 'status'], name='orders_ship_action_type_idx'),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['order'],
                condition=models.Q(action='cancel_shipping', status='succeeded'),
                name='uniq_success_cancel_shipping',
            ),
        ]

    def __str__(self):
        return f'发货操作#{self.id} 订单:{self.order_id} {self.action}/{self.status}'
```

- [ ] **Step 4: 生成迁移并检查只包含预期模型**

Run:

```bash
cd backend
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py makemigrations orders --name ordershippingaction
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py sqlmigrate orders 0028
```

Expected:

- 生成 `backend/orders/migrations/0028_ordershippingaction.py`。
- SQL 包含 `orders_ordershippingaction` 表。
- PostgreSQL SQL 包含条件唯一索引，条件为 `action = 'cancel_shipping' AND status = 'succeeded'`。

- [ ] **Step 5: 注册 Django Admin**

```python
# backend/orders/admin.py
from .models import OrderShippingAction


@admin.register(OrderShippingAction)
class OrderShippingActionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order',
        'action',
        'status',
        'operator',
        'wechat_sync_required',
        'wechat_synced',
        'created_at',
    )
    list_filter = ('action', 'status', 'wechat_sync_required', 'wechat_synced', 'created_at')
    search_fields = ('order__order_number', 'operator__username', 'reason')
    list_select_related = ('order', 'operator')
    readonly_fields = (
        'order',
        'action',
        'status',
        'shipping_snapshot',
        'operator',
        'reason',
        'wechat_sync_required',
        'wechat_synced',
        'wechat_response',
        'created_at',
    )
```

- [ ] **Step 6: 运行模型测试和迁移检查**

Run:

```bash
cd backend
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py test orders.tests.test_shipping_actions.ShippingActionModelTests -v 2
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py makemigrations --check --dry-run
```

Expected: 2 tests PASS；迁移检查输出 `No changes detected`。

- [ ] **Step 7: 提交**

```bash
git add backend/orders/models.py backend/orders/migrations/0028_ordershippingaction.py backend/orders/admin.py backend/orders/tests/test_shipping_actions.py
git commit -m "feat: 新增发货操作记录模型"
```

### Task 2: 建立取消发货领域服务与受控状态回退

**Files:**
- Create: `backend/orders/shipping_action_service.py`
- Modify: `backend/orders/state_machine.py`
- Modify: `backend/orders/tests/test_shipping_actions.py`

- [ ] **Step 1: 写海尔识别、快照和取消事务失败测试**

在 `backend/orders/tests/test_shipping_actions.py` 增加：

```python
from unittest.mock import patch

from orders.models import OrderItem, OrderStatusHistory
from orders.shipping_action_service import (
    ShippingActionError,
    build_shipping_snapshot,
    cancel_shipping,
    is_haier_order,
)


class CancelShippingServiceTests(ShippingFixtureMixin, TestCase):
    def test_build_shipping_snapshot_contains_all_current_fields(self):
        snapshot = build_shipping_snapshot(self.order)
        self.assertEqual(snapshot['logistics_no'], 'KY4001016483553')
        self.assertEqual(snapshot['delivery_record_code'], 'DELIVERY-1')
        self.assertEqual(snapshot['sn_code'], 'SN-1')
        self.assertEqual(snapshot['shipping_info']['shipping_list'][0]['express_company'], 'KYSY')
        self.assertEqual(snapshot['delivery_images'], ['https://cdn.example.com/delivery.jpg'])

    def test_local_child_order_is_not_treated_as_haier(self):
        self.order.order_type = 'local'
        self.order.save(update_fields=['order_type'])
        self.assertFalse(is_haier_order(self.order))

    def test_haier_order_is_detected_by_each_legacy_signal(self):
        self.order.order_type = 'haier'
        self.assertTrue(is_haier_order(self.order))

        self.order.order_type = 'main'
        self.order.haier_so_id = 'SO-1'
        self.assertTrue(is_haier_order(self.order))

        self.order.haier_so_id = ''
        self.order.haier_order_no = 'H-1'
        self.assertTrue(is_haier_order(self.order))

        self.order.haier_order_no = ''
        self.order.haier_status = 'confirmed'
        self.assertTrue(is_haier_order(self.order))

        self.order.haier_status = ''
        self.product.source = 'haier'
        self.product.save(update_fields=['source'])
        self.assertTrue(is_haier_order(self.order))

    @patch('users.services.create_notification')
    def test_cancel_shipping_restores_paid_and_preserves_snapshot(self, notify):
        action = cancel_shipping(
            order_id=self.order.id,
            operator=self.operator,
            reason='物流单号填写错误',
        )

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'paid')
        self.assertEqual(self.order.logistics_no, '')
        self.assertEqual(self.order.delivery_record_code, '')
        self.assertEqual(self.order.sn_code, '')
        self.assertEqual(self.order.shipping_info, {})
        self.assertEqual(self.order.delivery_images, [])
        self.assertEqual(action.action, 'cancel_shipping')
        self.assertEqual(action.status, 'succeeded')
        self.assertEqual(action.shipping_snapshot['logistics_no'], 'KY4001016483553')
        self.assertTrue(OrderStatusHistory.objects.filter(
            order=self.order,
            from_status='shipped',
            to_status='paid',
            note='取消发货：物流单号填写错误',
        ).exists())
        notify.assert_not_called()

    def test_cancel_shipping_rejects_invalid_reason_status_haier_and_second_cancel(self):
        with self.assertRaisesMessage(ShippingActionError, '取消原因不能为空'):
            cancel_shipping(self.order.id, self.operator, '   ')

        self.order.status = 'paid'
        self.order.save(update_fields=['status'])
        with self.assertRaisesMessage(ShippingActionError, '仅已发货订单可以取消发货'):
            cancel_shipping(self.order.id, self.operator, '测试')

        self.order.status = 'shipped'
        self.order.order_type = 'haier'
        self.order.save(update_fields=['status', 'order_type'])
        with self.assertRaisesMessage(ShippingActionError, '海尔订单不支持取消发货'):
            cancel_shipping(self.order.id, self.operator, '测试')

        self.order.order_type = 'local'
        self.order.save(update_fields=['order_type'])
        cancel_shipping(self.order.id, self.operator, '第一次取消')
        self.order.status = 'shipped'
        self.order.save(update_fields=['status'])
        with self.assertRaisesMessage(ShippingActionError, '该订单已使用取消发货机会'):
            cancel_shipping(self.order.id, self.operator, '第二次取消')
```

- [ ] **Step 2: 运行服务测试确认模块不存在**

Run:

```bash
cd backend
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py test orders.tests.test_shipping_actions.CancelShippingServiceTests -v 2
```

Expected: FAIL，导入 `orders.shipping_action_service` 失败。

- [ ] **Step 3: 增加受控状态回退方法**

在 `backend/orders/state_machine.py` 的 `transition` 后增加专用方法，不把 `shipped -> paid` 加入通用 `TRANSITIONS`：

```python
    @classmethod
    @transaction.atomic
    def reverse_shipping(cls, order, operator=None, note: str = ''):
        """仅供取消发货服务使用的 shipped -> paid 回退。"""
        if order.status != OrderStatus.SHIPPED.value:
            raise ValueError('仅已发货订单可以取消发货')

        old_status = order.status
        new_status = OrderStatus.PAID.value
        order.status = new_status
        order.updated_at = timezone.now()
        order.save(update_fields=['status', 'updated_at'])

        from .models import OrderStatusHistory
        OrderStatusHistory.objects.create(
            order=order,
            from_status=old_status,
            to_status=new_status,
            operator=operator,
            note=note,
        )

        # paid 和 shipped 都计入销量；只运行销量边界逻辑，避免重复触发
        # 通用“支付成功”副作用。
        cls._handle_sales_count_change(order, old_status, new_status)
        try:
            from .analytics import OrderAnalytics
            OrderAnalytics.on_order_status_changed(order.id)
        except Exception:
            pass
        return order
```

- [ ] **Step 4: 创建领域服务**

创建 `backend/orders/shipping_action_service.py`：

```python
from copy import deepcopy

from django.db import IntegrityError, transaction

from catalog.models import Product
from .models import Order, OrderShippingAction
from .state_machine import OrderStateMachine


class ShippingActionError(ValueError):
    pass


def is_haier_order(order: Order) -> bool:
    if order.order_type == 'haier':
        return True
    if order.haier_so_id or order.haier_order_no or order.haier_status:
        return True

    items = list(order.items.all())
    if any(
        getattr(item.product, 'source', None) == Product.SOURCE_HAIER
        for item in items
        if item.product_id
    ):
        return True
    return bool(
        not items
        and order.product_id
        and getattr(order.product, 'source', None) == Product.SOURCE_HAIER
    )


def build_shipping_snapshot(order: Order) -> dict:
    return {
        'logistics_no': order.logistics_no or '',
        'shipping_info': deepcopy(order.shipping_info or {}),
        'delivery_record_code': order.delivery_record_code or '',
        'sn_code': order.sn_code or '',
        'delivery_images': deepcopy(order.delivery_images or []),
    }


def get_successful_cancel_action(order: Order):
    return order.shipping_actions.filter(
        action='cancel_shipping',
        status='succeeded',
    ).order_by('-created_at', '-id').first()


def get_shipping_capabilities(order: Order) -> dict:
    cached = getattr(order, '_shipping_capabilities_cache', None)
    if cached is not None:
        return cached

    actions = list(order.shipping_actions.all())
    successful_cancel = next(
        (
            action for action in actions
            if action.action == 'cancel_shipping' and action.status == 'succeeded'
        ),
        None,
    )
    successful_reship = any(
        action.action == 'reship' and action.status == 'succeeded'
        for action in actions
    )
    pending = successful_cancel is not None and not successful_reship
    capabilities = {
        'can_cancel_shipping': (
            order.status == 'shipped'
            and not is_haier_order(order)
            and successful_cancel is None
        ),
        'is_reshipment_pending': order.status == 'paid' and pending,
        'reship_requires_wechat_sync': (
            order.status == 'paid'
            and pending
            and bool(successful_cancel.wechat_sync_required)
        ),
        'shipping_cancel_count': 1 if successful_cancel else 0,
    }
    order._shipping_capabilities_cache = capabilities
    return capabilities


@transaction.atomic
def cancel_shipping(order_id: int, operator, reason: str) -> OrderShippingAction:
    normalized_reason = (reason or '').strip()
    if not normalized_reason:
        raise ShippingActionError('取消原因不能为空')
    if len(normalized_reason) > 200:
        raise ShippingActionError('取消原因不能超过200个字符')

    order = (
        Order.objects.select_for_update()
        .select_related('product', 'user')
        .prefetch_related('items__product', 'shipping_actions', 'shipping_syncs')
        .get(pk=order_id)
    )
    if any(
        action.action == 'cancel_shipping' and action.status == 'succeeded'
        for action in order.shipping_actions.all()
    ):
        raise ShippingActionError('该订单已使用取消发货机会')
    if order.status != 'shipped':
        raise ShippingActionError('仅已发货订单可以取消发货')
    if is_haier_order(order):
        raise ShippingActionError('海尔订单不支持取消发货')

    snapshot = build_shipping_snapshot(order)
    prior_wechat_sync = any(
        sync.status == 'succeeded'
        for sync in order.shipping_syncs.all()
    )
    try:
        action = OrderShippingAction.objects.create(
            order=order,
            action='cancel_shipping',
            status='succeeded',
            shipping_snapshot=snapshot,
            operator=operator,
            reason=normalized_reason,
            wechat_sync_required=prior_wechat_sync,
            wechat_synced=False,
        )
    except IntegrityError as exc:
        raise ShippingActionError('该订单已使用取消发货机会') from exc

    order.logistics_no = ''
    order.shipping_info = {}
    order.delivery_record_code = ''
    order.sn_code = ''
    order.delivery_images = []
    order.save(update_fields=[
        'logistics_no',
        'shipping_info',
        'delivery_record_code',
        'sn_code',
        'delivery_images',
    ])
    OrderStateMachine.reverse_shipping(
        order,
        operator=operator,
        note=f'取消发货：{normalized_reason}',
    )
    return action
```

- [ ] **Step 5: 运行服务测试**

Run:

```bash
cd backend
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py test orders.tests.test_shipping_actions.CancelShippingServiceTests -v 2
```

Expected: 全部 PASS。

- [ ] **Step 6: 检查状态机通用转换没有被放宽**

Run:

```bash
cd backend
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py shell -c "from orders.state_machine import OrderStateMachine; print(OrderStateMachine.can_transition('shipped', 'paid'))"
```

Expected: 输出 `False`。取消发货只能通过 `reverse_shipping()`。

- [ ] **Step 7: 提交**

```bash
git add backend/orders/shipping_action_service.py backend/orders/state_machine.py backend/orders/tests/test_shipping_actions.py
git commit -m "feat: 新增取消发货领域服务"
```

### Task 3: 增加取消发货接口、能力字段和管理员历史接口

**Files:**
- Modify: `backend/orders/serializers.py`
- Modify: `backend/orders/views.py`
- Modify: `backend/orders/tests/test_shipping_actions.py`

- [ ] **Step 1: 写 API 和序列化失败测试**

在 `backend/orders/tests/test_shipping_actions.py` 增加：

```python
from rest_framework.reverse import reverse
from rest_framework.test import APIClient

from orders.serializers import OrderSerializer


class ShippingActionApiTests(ShippingFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(self.operator)

    def test_order_serializer_exposes_shipping_capabilities(self):
        data = OrderSerializer(self.order).data
        self.assertTrue(data['can_cancel_shipping'])
        self.assertFalse(data['is_reshipment_pending'])
        self.assertFalse(data['reship_requires_wechat_sync'])
        self.assertEqual(data['shipping_cancel_count'], 0)

    def test_admin_can_cancel_shipping_through_api(self):
        response = self.client.patch(
            reverse('order-cancel-shipping', args=[self.order.id]),
            {'reason': '仓库取消出库'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['status'], 'paid')
        self.assertFalse(response.json()['can_cancel_shipping'])
        self.assertTrue(response.json()['is_reshipment_pending'])
        self.assertEqual(response.json()['shipping_cancel_count'], 1)

    def test_customer_cannot_cancel_shipping_or_read_history(self):
        self.client.force_authenticate(self.user)
        cancel_response = self.client.patch(
            reverse('order-cancel-shipping', args=[self.order.id]),
            {'reason': '测试'},
            format='json',
        )
        history_response = self.client.get(
            reverse('order-shipping-actions', args=[self.order.id]),
        )
        self.assertEqual(cancel_response.status_code, 403)
        self.assertEqual(history_response.status_code, 403)

    def test_history_endpoint_returns_snapshot_for_admin(self):
        cancel_shipping(self.order.id, self.operator, '物流单号填写错误')
        response = self.client.get(
            reverse('order-shipping-actions', args=[self.order.id]),
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()[0]['action'], 'cancel_shipping')
        self.assertEqual(
            response.json()[0]['shipping_snapshot']['logistics_no'],
            'KY4001016483553',
        )
        self.assertEqual(response.json()[0]['operator_username'], 'shipping-admin')

    def test_cancel_shipping_api_returns_confirmed_business_messages(self):
        response = self.client.patch(
            reverse('order-cancel-shipping', args=[self.order.id]),
            {'reason': '   '},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], '取消原因不能为空')
```

- [ ] **Step 2: 运行 API 测试确认字段和路由不存在**

Run:

```bash
cd backend
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py test orders.tests.test_shipping_actions.ShippingActionApiTests -v 2
```

Expected: FAIL，能力字段或 action 路由不存在。

- [ ] **Step 3: 增加操作记录序列化器和能力字段**

修改 `backend/orders/serializers.py`：

```python
from .models import OrderShippingAction
from .shipping_action_service import get_shipping_capabilities, is_haier_order


class OrderShippingActionSerializer(serializers.ModelSerializer):
    operator_username = serializers.CharField(
        source='operator.username',
        read_only=True,
        allow_null=True,
    )
    action_label = serializers.CharField(source='get_action_display', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = OrderShippingAction
        fields = [
            'id',
            'action',
            'action_label',
            'status',
            'status_label',
            'shipping_snapshot',
            'operator',
            'operator_username',
            'reason',
            'wechat_sync_required',
            'wechat_synced',
            'wechat_response',
            'created_at',
        ]
        read_only_fields = fields
```

在 `OrderSerializer` 增加字段：

```python
    can_cancel_shipping = serializers.SerializerMethodField()
    is_reshipment_pending = serializers.SerializerMethodField()
    reship_requires_wechat_sync = serializers.SerializerMethodField()
    shipping_cancel_count = serializers.SerializerMethodField()
```

把四个字段加入 `Meta.fields`，并增加：

```python
    def _shipping_capabilities(self, obj: Order) -> dict:
        return get_shipping_capabilities(obj)

    def get_can_cancel_shipping(self, obj: Order) -> bool:
        return self._shipping_capabilities(obj)['can_cancel_shipping']

    def get_is_reshipment_pending(self, obj: Order) -> bool:
        return self._shipping_capabilities(obj)['is_reshipment_pending']

    def get_reship_requires_wechat_sync(self, obj: Order) -> bool:
        return self._shipping_capabilities(obj)['reship_requires_wechat_sync']

    def get_shipping_cancel_count(self, obj: Order) -> int:
        return self._shipping_capabilities(obj)['shipping_cancel_count']

    def get_is_haier_order(self, obj: Order) -> bool:
        return is_haier_order(obj)
```

删除原 `get_is_haier_order()` 中重复的判断实现，保留上面的统一调用。

- [ ] **Step 4: 增加两个 ViewSet action 并预取记录**

修改 `backend/orders/views.py` 的模型和序列化器导入：

```python
from .models import OrderShippingAction
from .serializers import OrderShippingActionSerializer
from .shipping_action_service import ShippingActionError, cancel_shipping
```

在 `get_queryset()` 的 `prefetch_related()` 增加：

```python
            'shipping_actions',
            'shipping_actions__operator',
            'shipping_syncs',
```

在 `OrderViewSet` 增加：

```python
    def _is_shipping_operator(self, user) -> bool:
        return bool(user.is_staff or getattr(user, 'role', '') == 'support')

    @action(
        detail=True,
        methods=['patch'],
        permission_classes=[IsAuthenticated],
        url_path='cancel_shipping',
    )
    def cancel_shipping_action(self, request, pk=None):
        if not self._is_shipping_operator(request.user):
            return Response({'detail': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
        try:
            action_record = cancel_shipping(
                order_id=self.get_object().id,
                operator=request.user,
                reason=request.data.get('reason', ''),
            )
            order = self.get_queryset().get(pk=action_record.order_id)
            return Response(self.get_serializer(order).data, status=status.HTTP_200_OK)
        except ShippingActionError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='shipping_actions',
    )
    def shipping_actions(self, request, pk=None):
        if not self._is_shipping_operator(request.user):
            return Response({'detail': 'Not allowed'}, status=status.HTTP_403_FORBIDDEN)
        order = self.get_object()
        queryset = OrderShippingAction.objects.filter(order=order).select_related(
            'operator',
        ).order_by('-created_at', '-id')
        return Response(
            OrderShippingActionSerializer(queryset, many=True).data,
            status=status.HTTP_200_OK,
        )
```

DRF action 的方法名会生成以下路由名：

- `order-cancel-shipping-action` 如果保留方法名 `cancel_shipping_action`。
- 为匹配测试要求，给装饰器增加 `url_name='cancel-shipping'`。
- `shipping_actions` 增加 `url_name='shipping-actions'`。

最终装饰器必须明确为：

```python
@action(
    detail=True,
    methods=['patch'],
    permission_classes=[IsAuthenticated],
    url_path='cancel_shipping',
    url_name='cancel-shipping',
)
```

```python
@action(
    detail=True,
    methods=['get'],
    permission_classes=[IsAuthenticated],
    url_path='shipping_actions',
    url_name='shipping-actions',
)
```

- [ ] **Step 5: 运行 API 测试**

Run:

```bash
cd backend
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py test orders.tests.test_shipping_actions.ShippingActionApiTests -v 2
```

Expected: 全部 PASS。

- [ ] **Step 6: 验证列表查询没有明显 N+1**

在测试中增加：

```python
from django.db import connection
from django.test.utils import CaptureQueriesContext


    def test_order_list_prefetches_shipping_capability_relations(self):
        with CaptureQueriesContext(connection) as one_order_queries:
            response = self.client.get(reverse('order-list'))
        self.assertEqual(response.status_code, 200)

        Order.objects.create(
            user=self.user,
            product=self.product,
            quantity=1,
            total_amount=Decimal('100.00'),
            actual_amount=Decimal('100.00'),
            status='shipped',
        )
        with CaptureQueriesContext(connection) as two_order_queries:
            response = self.client.get(reverse('order-list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(two_order_queries), len(one_order_queries))
```

Run:

```bash
cd backend
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py test orders.tests.test_shipping_actions.ShippingActionApiTests.test_order_list_prefetches_shipping_capability_relations -v 2
```

Expected: PASS，添加第二个订单后查询数保持不变。

- [ ] **Step 7: 提交**

```bash
git add backend/orders/serializers.py backend/orders/views.py backend/orders/tests/test_shipping_actions.py
git commit -m "feat: 新增取消发货与历史查询接口"
```

### Task 4: 将现有发货接口接入首次发货和重新发货审计

**Files:**
- Modify: `backend/orders/shipping_action_service.py`
- Verify: `backend/orders/wechat_shipping_service.py`
- Modify: `backend/orders/views.py`
- Modify: `backend/orders/tests/test_shipping_actions.py`

- [ ] **Step 1: 写重新发货成功和失败回滚测试**

在 `backend/orders/tests/test_shipping_actions.py` 增加：

```python
from django.test import override_settings

from orders.models import OrderShippingSync, Payment


class ReshipApiTests(ShippingFixtureMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(self.operator)
        Payment.objects.create(
            order=self.order,
            amount=self.order.actual_amount,
            method='wechat',
            status='succeeded',
            logs=[{'transaction_id': '4200000000000000000000000001'}],
        )
        OrderShippingSync.objects.create(
            order=self.order,
            status='succeeded',
            payload={'shipping_list': [{'tracking_no': 'OLD001'}]},
            response={'errcode': 0, 'errmsg': 'ok'},
        )
        cancel_shipping(self.order.id, self.operator, '原物流信息错误')
        self.order.refresh_from_db()

    @override_settings(WECHAT_SHIPPING_SYNC_ENABLED=True)
    @patch('orders.wechat_shipping_service.upload_shipping_info')
    def test_wechat_reship_success_records_action_and_ships_order(self, upload):
        upload.return_value = (True, {'errcode': 0, 'errmsg': 'ok'}, '')
        response = self.client.patch(
            reverse('order-ship', args=[self.order.id]),
            {
                'express_company': 'KYSY',
                'logistics_no': 'KY4001016483553',
                'item_desc': '本地测试商品*1',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'shipped')
        self.assertFalse(response.json()['is_reshipment_pending'])
        self.assertFalse(response.json()['can_cancel_shipping'])
        action = self.order.shipping_actions.get(action='reship', status='succeeded')
        self.assertTrue(action.wechat_sync_required)
        self.assertTrue(action.wechat_synced)
        self.assertEqual(action.shipping_snapshot['logistics_no'], 'KY4001016483553')

    @override_settings(WECHAT_SHIPPING_SYNC_ENABLED=True)
    @patch('orders.wechat_shipping_service.upload_shipping_info')
    def test_wechat_reship_10060003_rolls_back_and_records_failed_attempt(self, upload):
        upload.return_value = (
            False,
            {'errcode': 10060003, 'errmsg': 'reship used'},
            'reship used',
        )
        response = self.client.patch(
            reverse('order-ship', args=[self.order.id]),
            {
                'express_company': 'KYSY',
                'logistics_no': 'KY4001016483553',
                'item_desc': '本地测试商品*1',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['detail'], '该支付单已使用微信重新发货机会')
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'paid')
        self.assertEqual(self.order.logistics_no, '')
        self.assertFalse(self.order.shipping_actions.filter(
            action='reship',
            status='succeeded',
        ).exists())
        failed = self.order.shipping_actions.get(action='reship', status='failed')
        self.assertEqual(failed.shipping_snapshot['logistics_no'], 'KY4001016483553')
        self.assertEqual(failed.wechat_response['errcode'], 10060003)

    @override_settings(WECHAT_SHIPPING_SYNC_ENABLED=False)
    def test_required_wechat_reship_is_rejected_when_sync_is_disabled(self):
        response = self.client.patch(
            reverse('order-ship', args=[self.order.id]),
            {
                'express_company': 'KYSY',
                'logistics_no': 'KY4001016483553',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['detail'],
            '微信发货同步已关闭，无法重新发货',
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'paid')

    def test_non_wechat_reship_only_updates_local_state(self):
        self.order.shipping_actions.filter(action='cancel_shipping').update(
            wechat_sync_required=False,
        )
        with patch('orders.wechat_shipping_service.upload_shipping_info') as upload:
            response = self.client.patch(
                reverse('order-ship', args=[self.order.id]),
                {
                    'express_company': 'KYSY',
                    'logistics_no': 'KY4001016483553',
                },
                format='json',
            )
        self.assertEqual(response.status_code, 200, response.content)
        upload.assert_not_called()
        self.assertTrue(self.order.shipping_actions.filter(
            action='reship',
            status='succeeded',
            wechat_sync_required=False,
            wechat_synced=False,
        ).exists())
```

补充首次发货回归测试：

```python
    @override_settings(WECHAT_SHIPPING_SYNC_ENABLED=False)
    def test_first_ship_records_ship_action(self):
        first_order = Order.objects.create(
            user=self.user,
            product=self.product,
            quantity=1,
            total_amount=Decimal('100.00'),
            actual_amount=Decimal('100.00'),
            status='paid',
        )
        response = self.client.patch(
            reverse('order-ship', args=[first_order.id]),
            {'express_company': 'KYSY', 'logistics_no': 'FIRST001'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()['can_cancel_shipping'])
        self.assertFalse(response.json()['is_reshipment_pending'])
        self.assertTrue(first_order.shipping_actions.filter(
            action='ship',
            status='succeeded',
        ).exists())
```

- [ ] **Step 2: 运行测试确认现有发货流程没有审计和回滚失败记录**

Run:

```bash
cd backend
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py test orders.tests.test_shipping_actions.ReshipApiTests -v 2
```

Expected: FAIL，缺少 `ship/reship` 记录和失败尝试记录。

- [ ] **Step 3: 增加领域服务辅助函数**

在 `backend/orders/shipping_action_service.py` 增加：

```python
def get_shipping_context(order: Order) -> dict:
    capabilities = get_shipping_capabilities(order)
    return {
        'action': 'reship' if capabilities['is_reshipment_pending'] else 'ship',
        'is_reship': capabilities['is_reshipment_pending'],
        'wechat_sync_required': (
            capabilities['reship_requires_wechat_sync']
            if capabilities['is_reshipment_pending']
            else False
        ),
    }


def sanitize_wechat_response(response: dict | None, error: str = '') -> dict:
    response = response if isinstance(response, dict) else {}
    result = {
        key: response[key]
        for key in ('errcode', 'errmsg')
        if key in response
    }
    if error:
        result['error'] = str(error)[:500]
    return result


def create_successful_shipping_action(
    *,
    order: Order,
    action: str,
    operator,
    snapshot: dict,
    wechat_sync_required: bool,
    wechat_synced: bool,
    wechat_response: dict | None,
) -> OrderShippingAction:
    return OrderShippingAction.objects.create(
        order=order,
        action=action,
        status='succeeded',
        shipping_snapshot=snapshot,
        operator=operator,
        wechat_sync_required=wechat_sync_required,
        wechat_synced=wechat_synced,
        wechat_response=sanitize_wechat_response(wechat_response),
    )


def create_failed_reship_action(
    *,
    order_id: int,
    operator,
    snapshot: dict,
    response: dict | None,
    error: str,
) -> OrderShippingAction:
    with transaction.atomic():
        order = Order.objects.select_for_update().get(pk=order_id)
        return OrderShippingAction.objects.create(
            order=order,
            action='reship',
            status='failed',
            shipping_snapshot=deepcopy(snapshot),
            operator=operator,
            reason='微信重新发货同步失败',
            wechat_sync_required=True,
            wechat_synced=False,
            wechat_response=sanitize_wechat_response(response, error),
        )
```

- [ ] **Step 4: 扩展微信同步异常携带结构化上下文**

修改 `backend/orders/views.py`：

```python
class _WechatShippingSyncException(Exception):
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        response: Dict | None = None,
        error: str = '',
    ):
        self.message = message
        self.status_code = status_code
        self.response = response or {}
        self.error = error
        super().__init__(message)
```

微信返回失败时改为：

```python
raise _WechatShippingSyncException(
    _wechat_shipping_error_message(err, resp),
    response=resp,
    error=err or '',
)
```

未知异常改为：

```python
raise _WechatShippingSyncException(
    '微信发货同步异常，请稍后重试',
    status.HTTP_502_BAD_GATEWAY,
    error='unexpected_exception',
)
```

- [ ] **Step 5: 在 `/ship/` 事务中识别并记录发货类型**

在进入 `transaction.atomic()` 后、写物流字段前：

```python
from .shipping_action_service import (
    build_shipping_snapshot,
    create_failed_reship_action,
    create_successful_shipping_action,
    get_shipping_context,
)

shipping_context = get_shipping_context(order)
is_reship = shipping_context['is_reship']
requires_wechat_reship = shipping_context['wechat_sync_required']

if is_reship and requires_wechat_reship:
    if not getattr(settings, 'WECHAT_SHIPPING_SYNC_ENABLED', False):
        raise ValueError('微信发货同步已关闭，无法重新发货')
    should_sync = True
else:
    should_sync = (
        not is_reship
        and getattr(settings, 'WECHAT_SHIPPING_SYNC_ENABLED', False)
        and order.payments.filter(status='succeeded', method='wechat').exists()
    )
```

构造 `shipping_info` 后，在保存订单前创建供成功或失败记录使用的尝试快照：

```python
attempted_snapshot = {
    'logistics_no': tracking_number or '',
    'shipping_info': shipping_info,
    'delivery_record_code': order.delivery_record_code or '',
    'sn_code': order.sn_code or '',
    'delivery_images': order.delivery_images or [],
}
wechat_response = {}
```

微信调用成功后保存 `resp`：

```python
wechat_response = resp or {}
```

微信同步完成并且状态转换仍在同一事务内时创建成功记录：

```python
create_successful_shipping_action(
    order=order,
    action=shipping_context['action'],
    operator=user,
    snapshot=attempted_snapshot,
    wechat_sync_required=should_sync,
    wechat_synced=wechat_synced,
    wechat_response=wechat_response,
)
```

`transaction.on_commit(_send_ship_notification)` 保持不变，因此失败回滚不会通知客户。

退出 `transaction.atomic()` 后、构造响应前重新查询订单，避免复用状态变更前已经缓存的能力字段和关联记录：

```python
order = self.get_queryset().get(pk=order.id)
serializer = self.get_serializer(order)
return Response(serializer.data, status=status.HTTP_200_OK)
```

- [ ] **Step 6: 主事务回滚后记录失败的微信重发**

在 `except _WechatShippingSyncException as e:` 中：

```python
if locals().get('is_reship') and locals().get('attempted_snapshot'):
    try:
        create_failed_reship_action(
            order_id=order.id,
            operator=user,
            snapshot=attempted_snapshot,
            response=e.response,
            error=e.error or e.message,
        )
    except Exception:
        logger.exception(
            'failed to persist reship failure audit',
            extra={'order_id': order.id},
        )
return Response({'detail': e.message}, status=e.status_code)
```

失败审计必须在主 `atomic()` 已退出后执行，否则会随主事务一起回滚。

- [ ] **Step 7: 保留 `10060023` 幂等成功并增加测试**

`backend/orders/wechat_shipping_service.py` 当前把 `10060023` 视为成功。保留该逻辑，因为它明确表示微信当前物流与本次请求相同，可用于处理“前一次请求已到达微信但本地未提交”的重试场景。

增加测试：

```python
    @override_settings(WECHAT_SHIPPING_SYNC_ENABLED=True)
    @patch('orders.wechat_shipping_service.upload_shipping_info')
    def test_reship_10060023_is_accepted_as_idempotent_success(self, upload):
        upload.return_value = (
            True,
            {'errcode': 10060023, 'errmsg': '发货信息未更新'},
            '',
        )
        response = self.client.patch(
            reverse('order-ship', args=[self.order.id]),
            {
                'express_company': 'KYSY',
                'logistics_no': 'KY4001016483553',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(self.order.shipping_actions.filter(
            action='reship',
            status='succeeded',
            wechat_response__errcode=10060023,
        ).exists())
```

- [ ] **Step 8: 运行全部发货操作测试**

Run:

```bash
cd backend
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py test orders.tests.test_shipping_actions -v 2
```

Expected: 全部 PASS。

- [ ] **Step 9: 提交**

```bash
git add backend/orders/shipping_action_service.py backend/orders/views.py backend/orders/tests/test_shipping_actions.py
git commit -m "feat: 支持受控重新发货与失败审计"
```

### Task 5: 补齐并发、旧订单和回归测试

**Files:**
- Modify: `backend/orders/tests/test_shipping_actions.py`

- [ ] **Step 1: 增加旧订单、信用支付和海尔商品来源测试**

```python
class ShippingActionRegressionTests(ShippingFixtureMixin, TestCase):
    def test_legacy_order_without_ship_action_can_be_cancelled(self):
        self.assertFalse(self.order.shipping_actions.exists())
        action = cancel_shipping(self.order.id, self.operator, '旧订单纠错')
        self.assertEqual(action.shipping_snapshot['logistics_no'], 'KY4001016483553')

    def test_credit_order_can_cancel_and_reship_locally(self):
        cancel_shipping(self.order.id, self.operator, '信用订单纠错')
        self.client = APIClient()
        self.client.force_authenticate(self.operator)
        response = self.client.patch(
            reverse('order-ship', args=[self.order.id]),
            {'express_company': 'KYSY', 'logistics_no': 'CREDIT001'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(self.order.shipping_actions.filter(
            action='reship',
            status='succeeded',
            wechat_sync_required=False,
        ).exists())

    def test_order_item_with_haier_product_blocks_cancel(self):
        local_product = Product.objects.create(
            name='本地主商品',
            price=Decimal('100.00'),
            stock=10,
            source='local',
        )
        haier_product = Product.objects.create(
            name='海尔商品',
            price=Decimal('100.00'),
            stock=10,
            source='haier',
        )
        self.order.product = local_product
        self.order.save(update_fields=['product'])
        OrderItem.objects.create(
            order=self.order,
            product=haier_product,
            product_name=haier_product.name,
            quantity=1,
            unit_price=Decimal('100.00'),
            actual_amount=Decimal('100.00'),
        )
        with self.assertRaisesMessage(ShippingActionError, '海尔订单不支持取消发货'):
            cancel_shipping(self.order.id, self.operator, '测试')
```

- [ ] **Step 2: 增加 PostgreSQL 并发测试**

```python
from concurrent.futures import ThreadPoolExecutor
from django.db import close_old_connections, connection
from django.test import TransactionTestCase


class CancelShippingConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        user = get_user_model().objects.create_user(
            username='concurrent-buyer',
            password='pwd',
        )
        operator = get_user_model().objects.create_user(
            username='concurrent-admin',
            password='pwd',
            is_staff=True,
        )
        product = Product.objects.create(
            name='并发测试商品',
            price=Decimal('100.00'),
            stock=10,
            source='local',
        )
        order = Order.objects.create(
            user=user,
            product=product,
            quantity=1,
            total_amount=Decimal('100.00'),
            actual_amount=Decimal('100.00'),
            status='shipped',
            logistics_no='CONCURRENT001',
            shipping_info={
                'logistics_type': 1,
                'delivery_mode': 1,
                'shipping_list': [{
                    'express_company': 'KYSY',
                    'tracking_no': 'CONCURRENT001',
                }],
            },
        )
        self.order_id = order.id
        self.operator_id = operator.id

    def _cancel(self):
        close_old_connections()
        operator = get_user_model().objects.get(pk=self.operator_id)
        try:
            cancel_shipping(self.order_id, operator, '并发取消')
            return 'ok'
        except ShippingActionError as exc:
            return str(exc)
        finally:
            close_old_connections()

    def test_only_one_concurrent_cancel_succeeds(self):
        if connection.vendor != 'postgresql':
            self.skipTest('select_for_update concurrency semantics require PostgreSQL')
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: self._cancel(), range(2)))
        self.assertEqual(results.count('ok'), 1)
        self.assertEqual(results.count('该订单已使用取消发货机会'), 1)
        self.assertEqual(OrderShippingAction.objects.filter(
            order_id=self.order_id,
            action='cancel_shipping',
            status='succeeded',
        ).count(), 1)
```

- [ ] **Step 3: SQLite 运行全套测试**

Run:

```bash
cd backend
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py test orders.tests.test_shipping_actions -v 2
```

Expected: 功能测试 PASS；PostgreSQL 并发测试显示 SKIPPED。

- [ ] **Step 4: PostgreSQL 环境运行并发测试**

Run:

```bash
cd backend
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py test orders.tests.test_shipping_actions.CancelShippingConcurrencyTests -v 2 --settings=backend.settings.production
```

Expected: 在已配置测试 PostgreSQL 的 CI/预发布环境中 PASS。不得对生产数据库执行该命令。

- [ ] **Step 5: 运行订单与支付回归**

Run:

```bash
cd backend
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py test \
  orders.tests.test_shipping_actions \
  orders.tests.test_order_items \
  orders.tests.test_payments \
  orders.tests.test_serializer_payment_method \
  -v 2
```

Expected: 全部 PASS，PostgreSQL 专用测试在 SQLite 下仅有预期 SKIPPED。

- [ ] **Step 6: 提交**

```bash
git add backend/orders/tests/test_shipping_actions.py
git commit -m "test: 补充取消发货并发与回归覆盖"
```

### Task 6: 扩展 Merchant API 类型

**Files:**
- Modify: `merchant/src/services/types.ts`
- Modify: `merchant/src/services/api.ts`

- [ ] **Step 1: 增加完整物流和操作记录类型**

修改 `merchant/src/services/types.ts`：

```typescript
export interface ShippingItem {
  tracking_no?: string;
  express_company?: string;
  item_desc?: string;
  contact?: Record<string, string>;
}

export interface ShippingInfo {
  logistics_type?: number;
  delivery_mode?: number;
  is_all_delivered?: boolean | null;
  shipping_list?: ShippingItem[];
}

export interface LogisticsInfo {
  logistics_no?: string;
  delivery_record_code?: string;
  sn_code?: string;
  delivery_images?: string[];
  shipping_info?: ShippingInfo | null;
}

export interface ShippingSnapshot {
  logistics_no: string;
  shipping_info: ShippingInfo;
  delivery_record_code: string;
  sn_code: string;
  delivery_images: string[];
}

export interface OrderShippingAction {
  id: number;
  action: 'ship' | 'cancel_shipping' | 'reship';
  action_label: string;
  status: 'succeeded' | 'failed';
  status_label: string;
  shipping_snapshot: ShippingSnapshot;
  operator: number | null;
  operator_username: string | null;
  reason: string;
  wechat_sync_required: boolean;
  wechat_synced: boolean;
  wechat_response: {
    errcode?: number;
    errmsg?: string;
    error?: string;
  };
  created_at: string;
}
```

在 `Order` 增加：

```typescript
  can_cancel_shipping: boolean;
  is_reshipment_pending: boolean;
  reship_requires_wechat_sync: boolean;
  shipping_cancel_count: number;
```

- [ ] **Step 2: 增加 API 方法**

修改 `merchant/src/services/api.ts`：

```typescript
export const cancelShipping = (id: number, data: { reason: string }) =>
  request.patch(`/orders/${id}/cancel_shipping/`, data);

export const getShippingActions = (id: number) =>
  request.get(`/orders/${id}/shipping_actions/`);
```

- [ ] **Step 3: 运行 TypeScript 构建，确认页面尚未接入但类型有效**

Run:

```bash
cd merchant
npm run build
```

Expected: PASS。若现有代码因新增必填能力字段构造了局部 `Order` 字面量，给这些字面量补齐字段，不得把能力字段改为可选来掩盖类型错误。

- [ ] **Step 4: 提交**

```bash
git add merchant/src/services/types.ts merchant/src/services/api.ts
git commit -m "feat: 扩展商户端发货接口类型"
```

### Task 7: 增加 Merchant 取消发货交互与重新发货提示

**Files:**
- Modify: `merchant/src/pages/Orders/index.tsx`

- [ ] **Step 1: 增加导入和页面状态**

更新导入：

```typescript
import { cancelShipping, getShippingActions } from '@/services/api';
import type { Order, OrderShippingAction } from '@/services/types';
import { Alert } from 'antd';
```

实现时把新增名称合并到文件顶部已有的同模块 import，避免长期保留重复 import 语句。

在 `Orders()` 内新增：

```typescript
const [cancelShippingModalVisible, setCancelShippingModalVisible] = useState(false);
const [cancelShippingOrder, setCancelShippingOrder] = useState<Order | null>(null);
const [shippingActions, setShippingActions] = useState<OrderShippingAction[]>([]);
const [shippingActionsLoading, setShippingActionsLoading] = useState(false);
```

同时把 Merchant 的 `paid` 状态文案与后端统一为“待发货”：

```typescript
paid: { text: '待发货', color: 'blue' },
```

上面一行替换 `statusMap` 中当前的 `paid: { text: '已支付', color: 'blue' }`。

- [ ] **Step 2: 增加取消发货处理函数**

```typescript
const handleCancelShipping = (record: Order) => {
  setCancelShippingOrder(record);
  setCancelShippingModalVisible(true);
};

const handleCancelShippingSubmit = async (values: { reason: string }) => {
  if (!cancelShippingOrder) return false;
  try {
    await cancelShipping(cancelShippingOrder.id, {
      reason: values.reason.trim(),
    });
    message.success('取消发货成功');
    setCancelShippingModalVisible(false);
    setCancelShippingOrder(null);
    actionRef.current?.reload();
    return true;
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '取消发货失败');
    return false;
  }
};
```

- [ ] **Step 3: 只根据后端能力字段显示按钮**

在操作列 `render` 中，`record.status === 'shipped'` 的“完成”按钮前增加：

```tsx
if (record.can_cancel_shipping) {
  actions.push(
    <Button
      key="cancel-shipping"
      type="link"
      size="small"
      danger
      icon={<RollbackOutlined />}
      onClick={() => handleCancelShipping(record)}
    >
      取消发货
    </Button>
  );
}
```

不要在 Merchant 重复判断 `order_type`、支付方式或海尔字段。后端 `can_cancel_shipping` 是唯一按钮条件。

- [ ] **Step 4: 增加单弹窗确认和必填原因**

在现有发货弹窗后增加：

```tsx
<ModalForm
  title="取消发货"
  visible={cancelShippingModalVisible}
  onVisibleChange={(visible) => {
    setCancelShippingModalVisible(visible);
    if (!visible) setCancelShippingOrder(null);
  }}
  onFinish={handleCancelShippingSubmit}
  modalProps={{ destroyOnClose: true }}
  submitter={{
    searchConfig: {
      submitText: '确认取消发货',
      resetText: '取消',
    },
  }}
>
  <ProDescriptions
    column={1}
    dataSource={cancelShippingOrder || {}}
    style={{ marginBottom: 16 }}
  >
    <ProDescriptions.Item
      label="物流公司"
      render={() =>
        cancelShippingOrder?.logistics_info?.shipping_info?.shipping_list?.[0]
          ?.express_company || '-'
      }
    />
    <ProDescriptions.Item
      label="物流单号"
      render={() => cancelShippingOrder?.logistics_info?.logistics_no || '-'}
    />
  </ProDescriptions>
  <Alert
    type="warning"
    showIcon
    style={{ marginBottom: 16 }}
    message="取消发货风险提示"
    description={
      <>
        <div>取消后订单将恢复为“待发货”，当前物流信息会被清空。</div>
        <div>微信侧原发货记录无法撤销，再次发货将使用唯一一次重新发货机会。</div>
        <div>每个订单只能取消发货一次。</div>
      </>
    }
  />
  <ProFormTextArea
    name="reason"
    label="取消原因"
    placeholder="请输入取消原因"
    fieldProps={{ maxLength: 200, showCount: true }}
    rules={[
      { required: true, whitespace: true, message: '请输入取消原因' },
      { max: 200, message: '取消原因不能超过200个字符' },
    ]}
  />
</ModalForm>
```

`ModalForm` 自带提交 loading，提交期间不得再绑定额外可重复触发的按钮。

- [ ] **Step 5: 动态显示“重新发货”和微信机会提示**

把现有发货弹窗的标题属性改为：

```tsx
title={shippingOrder?.is_reshipment_pending ? '重新发货' : '订单发货'}
```

在现有 `<ModalForm>` 开始标签之后、`<ProFormRadio.Group name="delivery_mode">` 之前插入：

```tsx
{shippingOrder?.is_reshipment_pending &&
  shippingOrder.reship_requires_wechat_sync && (
    <Alert
      type="warning"
      showIcon
      style={{ marginBottom: 16 }}
      message="微信重新发货机会仅有一次"
      description="本次将更新微信发货信息，并使用该支付单唯一一次重新发货机会，提交后不可再次修改。"
    />
  )}
```

发货成功提示改为：

```typescript
message.success(shippingOrder.is_reshipment_pending ? '重新发货成功' : '发货成功');
```

- [ ] **Step 6: 运行 Merchant 构建**

Run:

```bash
cd merchant
npm run build
```

Expected: `tsc` 和 `vite build` 均 PASS。

- [ ] **Step 7: 手工冒烟取消与重新发货入口**

Run:

```bash
cd merchant
npm run dev
```

Expected manual checks:

1. 普通 `shipped` 且 `can_cancel_shipping=true` 的订单显示“取消发货”。
2. 海尔订单、已取消过发货的订单不显示按钮。
3. 弹窗显示当前物流、三条风险提示和必填原因。
4. 未输入原因不能提交。
5. 取消成功后列表刷新为“待发货”。
6. 再次点击“发货”时标题为“重新发货”。
7. `reship_requires_wechat_sync=true` 时显示唯一一次微信重发机会提示。
8. 请求期间提交按钮显示 loading，不能重复提交。

- [ ] **Step 8: 提交**

```bash
git add merchant/src/pages/Orders/index.tsx
git commit -m "feat: 新增商户端取消发货交互"
```

### Task 8: 在 Merchant 订单详情展示管理员发货历史

**Files:**
- Modify: `merchant/src/pages/Orders/index.tsx`

- [ ] **Step 1: 查询详情时同时加载操作记录**

替换 `handleViewDetail`：

```typescript
const handleViewDetail = async (record: Order) => {
  try {
    setShippingActionsLoading(true);
    const [orderResult, actionResult] = await Promise.all([
      getOrder(record.id),
      getShippingActions(record.id),
    ]);
    setCurrentOrder(orderResult as Order);
    setShippingActions((actionResult || []) as OrderShippingAction[]);
    setDetailVisible(true);
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '获取订单详情失败');
  } finally {
    setShippingActionsLoading(false);
  }
};
```

关闭 Drawer 时清空：

```tsx
onClose={() => {
  setDetailVisible(false);
  setCurrentOrder(null);
  setShippingActions([]);
}}
```

- [ ] **Step 2: 增加操作记录展示**

在订单详情基本信息和海尔信息之间增加：

```tsx
<div style={{ marginTop: 24 }}>
  <div style={{ marginBottom: 12, fontSize: 16, fontWeight: 600 }}>
    发货操作记录
  </div>
  <List
    loading={shippingActionsLoading}
    dataSource={shippingActions}
    locale={{ emptyText: '暂无发货操作记录' }}
    renderItem={(item) => {
      const snapshot = item.shipping_snapshot || {};
      const packages = snapshot.shipping_info?.shipping_list || [];
      return (
        <List.Item>
          <List.Item.Meta
            title={
              <Space>
                <span>{item.action_label}</span>
                <Tag color={item.status === 'succeeded' ? 'green' : 'red'}>
                  {item.status_label}
                </Tag>
                {item.wechat_sync_required && (
                  <Tag color={item.wechat_synced ? 'blue' : 'orange'}>
                    {item.wechat_synced ? '微信已同步' : '微信未同步'}
                  </Tag>
                )}
              </Space>
            }
            description={
              <Space direction="vertical" size={4}>
                <span>
                  操作人：{item.operator_username || '系统'} ·{' '}
                  {new Date(item.created_at).toLocaleString()}
                </span>
                {item.reason && <span>原因：{item.reason}</span>}
                <span>物流单号：{snapshot.logistics_no || '-'}</span>
                {packages.map((pkg, index) => (
                  <span key={`${pkg.tracking_no || 'package'}-${index}`}>
                    包裹 {index + 1}：{pkg.express_company || '-'} /{' '}
                    {pkg.tracking_no || '-'}
                  </span>
                ))}
                {Object.keys(item.wechat_response || {}).length > 0 && (
                  <span>
                    微信响应：{JSON.stringify(item.wechat_response)}
                  </span>
                )}
              </Space>
            }
          />
        </List.Item>
      );
    }}
  />
</div>
```

- [ ] **Step 3: 运行 Merchant 构建**

Run:

```bash
cd merchant
npm run build
```

Expected: PASS。

- [ ] **Step 4: 手工检查详情权限和展示**

Expected manual checks:

1. Merchant 管理员打开详情能看到首次发货、取消发货和重新发货记录。
2. 取消记录显示取消前旧物流快照。
3. 失败重发显示失败状态和脱敏微信响应。
4. 客户小程序订单接口和页面没有新增历史物流区域。

- [ ] **Step 5: 提交**

```bash
git add merchant/src/pages/Orders/index.tsx
git commit -m "feat: 展示发货操作历史"
```

### Task 9: 更新 API 文档并完成全链路验证

**Files:**
- Modify: `docs/api/api.md`
- Move: `docs/plan/2026-06-05-cancel-shipping-reship.md` -> `docs/plan/archive/2026-06-05-cancel-shipping-reship.md`

- [ ] **Step 1: 记录订单能力字段**

在订单响应字段说明增加：

```markdown
| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `can_cancel_shipping` | boolean | 当前管理员是否可执行取消发货 |
| `is_reshipment_pending` | boolean | 是否已取消发货且等待重新发货 |
| `reship_requires_wechat_sync` | boolean | 本次重新发货是否必须同步微信 |
| `shipping_cancel_count` | integer | 已成功取消发货次数，当前只可能为 0 或 1 |
```

- [ ] **Step 2: 记录取消发货和历史接口**

````markdown
### 取消发货

`PATCH /api/orders/{id}/cancel_shipping/`

仅管理员或客服可调用。订单必须为已发货、非海尔订单且从未成功取消过发货。

请求：

```json
{
  "reason": "物流单号填写错误"
}
```

成功后订单恢复为 `paid`，当前物流字段被清空，微信侧旧发货信息不会撤销。

### 查询发货操作记录

`GET /api/orders/{id}/shipping_actions/`

仅管理员或客服可调用。按时间倒序返回 `ship`、`cancel_shipping`、`reship` 操作及管理员可见物流快照。
````

- [ ] **Step 3: 后端完整验证**

Run:

```bash
cd backend
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py makemigrations --check --dry-run
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py check
UV_CACHE_DIR=/tmp/electric-uv-cache uv run python manage.py test \
  orders.tests.test_shipping_actions \
  orders.tests.test_order_items \
  orders.tests.test_payments \
  orders.tests.test_serializer_payment_method \
  -v 2
```

Expected:

- `No changes detected`
- Django system check 无错误
- 全部测试 PASS，只有 PostgreSQL 专用并发测试在 SQLite 下 SKIPPED

- [ ] **Step 4: Merchant 完整验证**

Run:

```bash
cd merchant
npm run build
```

Expected: `tsc` 和 Vite production build PASS。

- [ ] **Step 5: 检查接口和敏感信息边界**

Run:

```bash
rg -n "shipping_snapshot|wechat_response" frontend/src backend/orders/serializers.py merchant/src -S
```

Expected:

- `frontend/src` 无发货历史快照展示或调用。
- `OrderSerializer` 不包含 `shipping_snapshot`、`wechat_response`。
- 仅管理员专用 `OrderShippingActionSerializer` 和 Merchant 使用这些字段。

- [ ] **Step 6: 检查确认过的业务约束**

Run:

```bash
rg -n "cancel_shipping|reship|reverse_shipping|can_cancel_shipping|reship_requires_wechat_sync" backend/orders merchant/src docs/api/api.md -S
```

Expected:

- 只有专用领域服务调用 `reverse_shipping`。
- Merchant 按 `can_cancel_shipping` 控制按钮。
- 微信重发关闭时不会只更新本地状态。
- `10060003` 映射为“该支付单已使用微信重新发货机会”。

- [ ] **Step 7: 提交文档**

```bash
git add docs/api/api.md
git commit -m "docs: 更新取消发货接口说明"
```

- [ ] **Step 8: 归档已完成计划**

仅在代码完成、测试通过且以上提交都已完成后执行：

```bash
mkdir -p docs/plan/archive
mv docs/plan/2026-06-05-cancel-shipping-reship.md docs/plan/archive/2026-06-05-cancel-shipping-reship.md
git add docs/plan/archive/2026-06-05-cancel-shipping-reship.md
git commit -m "docs: 归档取消发货实施计划"
```

## Spec Coverage Check

1. 一次性取消发货、原因必填、物流清空、`shipped -> paid`：Task 2、Task 3。
2. 完整历史快照、操作人、微信同步状态和管理员历史接口：Task 1、Task 3、Task 8。
3. 海尔订单和历史海尔信号排除，本地子订单允许：Task 2、Task 5。
4. 所有支付方式允许本地取消，信用支付可本地重发：Task 4、Task 5。
5. 旧订单无 `ship` 记录仍能取消：Task 2、Task 5。
6. 微信首次发货与重新发货复用 `/ship/`，`10060003` 明确报错，`10060023` 幂等成功：Task 4。
7. 微信重发失败回滚本地状态并独立记录失败尝试：Task 4。
8. 每单最多一次成功取消和并发保护：Task 1、Task 2、Task 5。
9. 取消时不通知客户，重新发货成功沿用发货通知：Task 2、Task 4。
10. Merchant 单弹窗确认、风险提示、动态标题、微信机会提示和防重复提交：Task 7。
11. Merchant 详情展示管理员历史，客户侧不暴露快照：Task 8、Task 9。
12. 发布前迁移、后端回归、Merchant 构建和敏感边界检查：Task 9。

## Placeholder Scan

已检查：计划不包含 `TBD`、`TODO`、`implement later` 或没有明确实现方式的“补充处理”步骤。并发测试中共享 fixture 的最终结构、断言和运行环境均已明确。

## Type And Interface Consistency Check

1. 后端统一使用模型名 `OrderShippingAction` 和关联名 `shipping_actions`。
2. 动作值统一为 `ship`、`cancel_shipping`、`reship`。
3. 结果值统一为 `succeeded`、`failed`。
4. 订单能力字段统一为 `can_cancel_shipping`、`is_reshipment_pending`、`reship_requires_wechat_sync`、`shipping_cancel_count`。
5. API 路径统一为 `/orders/{id}/cancel_shipping/` 和 `/orders/{id}/shipping_actions/`。
6. Merchant 类型与后端序列化字段一致。
7. 物流快照统一包含 `logistics_no`、`shipping_info`、`delivery_record_code`、`sn_code`、`delivery_images`。
8. 微信失败审计仅保存 `errcode`、`errmsg` 和截断后的 `error`，不保存 openid、联系方式或完整请求载荷。
