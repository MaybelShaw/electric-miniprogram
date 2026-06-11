from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from backend.settings.env_config import EnvironmentConfig
from catalog.models import (
    Brand,
    Category,
    HomeBanner,
    HomeStoreCard,
    HomeStoreCardCategory,
    HomeStoreCardProduct,
    MediaImage,
    Product,
    ProductSKU,
    SpecialZone,
    SpecialZoneProduct,
)
from orders.models import Discount, DiscountTarget, Order, OrderItem
from stores.models import (
    Store,
    StoreCustomerGroup,
    StoreCustomerGroupMember,
    StoreCustomerGroupPrice,
    StoreMember,
)
from users.models import AccountStatement, AccountTransaction, Address, CreditAccount


DEMO_PREFIX = "cy_demo"


class Command(BaseCommand):
    help = "Seed a related storefront demo dataset for local development only."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm-dev",
            action="store_true",
            help="Required safety flag. Refuses to run without this flag.",
        )

    def handle(self, *args, **options):
        self._assert_development_database(options["confirm_dev"])
        with transaction.atomic():
            data = self._seed()

        self.stdout.write(self.style.SUCCESS("Seeded storefront demo data:"))
        self.stdout.write(f"- Store: {data['store'].name} (code={data['store'].code}, id={data['store'].id})")
        self.stdout.write(f"- Store admin: {data['store_admin'].username} / Demo@123456")
        self.stdout.write(f"- Platform admin: {data['platform_admin'].username} / Demo@123456")
        self.stdout.write(f"- Customers: {', '.join(user.username for user in data['customers'])} / Demo@123456")
        self.stdout.write(f"- Categories: {data['category_count']}")
        self.stdout.write(f"- Brands: {data['brand_count']}")
        self.stdout.write(f"- Products: {len(data['products'])}")
        self.stdout.write(f"- SKUs: {data['sku_count']}")
        self.stdout.write(f"- Store activities: {len(data['zones'])}")
        self.stdout.write(f"- Home banners: {data['banner_count']}")
        self.stdout.write(f"- Home store card: {data['card'].title}")

    def _assert_development_database(self, confirmed):
        if not confirmed:
            raise CommandError("Refusing to seed data without --confirm-dev.")
        if EnvironmentConfig.is_production():
            raise CommandError("Refusing to seed demo data when DJANGO_ENV=production.")

        settings_module = EnvironmentConfig.get_env("DJANGO_SETTINGS_MODULE", "")
        if "production" in settings_module.lower():
            raise CommandError(f"Refusing to seed demo data with production settings: {settings_module}")

        db_settings = connection.settings_dict
        engine = db_settings.get("ENGINE", "")
        db_name = str(db_settings.get("NAME", ""))
        if "postgresql" in engine and "dev" not in db_name.lower() and "test" not in db_name.lower():
            raise CommandError(f"Refusing to seed non-dev PostgreSQL database: {db_name}")

    def _seed(self):
        main_store = self._ensure_main_store()
        store = self._ensure_demo_store(main_store)
        users = self._ensure_users(main_store, store)
        categories = self._ensure_categories(store)
        brands = self._ensure_brands(store)
        products, sku_count = self._ensure_products(store, categories, brands)
        zones = self._ensure_zones(store, products)
        banner_count = self._ensure_banners(store, products, zones)
        card = self._ensure_home_store_card(store, categories, products)
        self._ensure_customer_groups(store, users["dealer"], products)
        self._ensure_discount(users["dealer"], products)
        self._ensure_order_and_finance(store, users["dealer"], products)

        return {
            "store": store,
            "store_admin": users["store_admin"],
            "platform_admin": users["platform_admin"],
            "customers": [users["customer"], users["dealer"]],
            "category_count": len(categories),
            "brand_count": len(brands),
            "products": products,
            "sku_count": sku_count,
            "zones": zones,
            "banner_count": banner_count,
            "card": card,
        }

    def _ensure_main_store(self):
        store = Store.objects.filter(is_main=True).order_by("id").first()
        if store is None:
            store, _ = Store.objects.get_or_create(
                code=Store.MAIN_STORE_CODE,
                defaults={
                    "name": "庆勋愉悦家",
                    "store_type": Store.TYPE_SELF_OPERATED,
                    "status": Store.STATUS_ACTIVE,
                    "is_main": True,
                    "allow_haier": True,
                    "show_on_home": True,
                    "home_order": 0,
                },
            )
        store.name = store.name or "庆勋愉悦家"
        store.store_type = Store.TYPE_SELF_OPERATED
        store.status = Store.STATUS_ACTIVE
        store.is_main = True
        store.allow_haier = True
        store.show_on_home = True
        store.home_order = 0
        store.save()
        return store

    def _ensure_demo_store(self, main_store):
        store, _ = Store.objects.update_or_create(
            code=f"{DEMO_PREFIX}_store",
            defaults={
                "name": "创艺测试店",
                "store_type": Store.TYPE_PARTNER,
                "platform_store": main_store,
                "status": Store.STATUS_ACTIVE,
                "is_main": False,
                "allow_haier": False,
                "show_on_home": True,
                "home_order": 10,
                "logo": "https://dummyimage.com/240x240/1f5c4a/ffffff&text=CY",
                "cover_image": "https://dummyimage.com/900x360/e8f3ef/1f5c4a&text=Chuangyi+Store",
                "description": "用于本地联调的创艺店铺，覆盖分类、品牌、商品、活动、轮播和客户分组价格。",
                "contact_phone": "0551-66000001",
                "address": "安徽省合肥市蜀山区创艺体验中心",
                "show_customer_group_name": False,
            },
        )
        return store

    def _ensure_users(self, main_store, store):
        User = get_user_model()
        users = {
            "platform_admin": self._ensure_user(
                User,
                "cy_demo_platform_admin",
                role="admin",
                phone="13900010001",
                is_staff=True,
                is_superuser=True,
            ),
            "store_admin": self._ensure_user(
                User,
                "cy_demo_store_admin",
                role="admin",
                phone="13900010002",
                is_staff=True,
            ),
            "customer": self._ensure_user(
                User,
                "cy_demo_customer",
                role="individual",
                phone="13900010003",
                openid="openid_cy_demo_customer",
            ),
            "dealer": self._ensure_user(
                User,
                "cy_demo_dealer",
                role="dealer",
                phone="13900010004",
                openid="openid_cy_demo_dealer",
            ),
        }

        StoreMember.objects.update_or_create(
            user=users["platform_admin"],
            store=main_store,
            defaults={"role": StoreMember.ROLE_PLATFORM_ADMIN, "status": StoreMember.STATUS_ACTIVE},
        )
        StoreMember.objects.update_or_create(
            user=users["store_admin"],
            store=store,
            defaults={"role": StoreMember.ROLE_STORE_ADMIN, "status": StoreMember.STATUS_ACTIVE},
        )

        self._ensure_address(users["customer"], "创艺客户", "13900010003")
        self._ensure_address(users["dealer"], "创艺经销商", "13900010004")
        return users

    def _ensure_user(self, User, username, *, role, phone, openid=None, is_staff=False, is_superuser=False):
        defaults = {
            "role": role,
            "phone": phone,
            "email": f"{username}@example.com",
            "is_staff": is_staff,
            "is_superuser": is_superuser,
        }
        if openid:
            defaults["openid"] = openid
        user, _ = User.objects.update_or_create(username=username, defaults=defaults)
        user.set_password("Demo@123456")
        user.save(update_fields=["password"])
        return user

    def _ensure_address(self, user, contact_name, phone):
        Address.objects.update_or_create(
            user=user,
            phone=phone,
            defaults={
                "contact_name": contact_name,
                "province": "安徽省",
                "city": "合肥市",
                "district": "蜀山区",
                "detail": "创艺测试小区 1 栋 101",
                "is_default": True,
            },
        )

    def _ensure_categories(self, store):
        spec = [
            ("厨房电器", "嵌入式厨电", ["蒸烤一体机", "洗碗机"]),
            ("全屋空气", "舒适系统", ["中央空调", "新风系统"]),
            ("智能家居", "智能控制", ["智能面板", "场景套装"]),
        ]
        categories = {}
        for major_order, (major_name, minor_name, item_names) in enumerate(spec, start=1):
            major = self._ensure_category(store, major_name, Category.LEVEL_MAJOR, None, major_order)
            categories[major_name] = major
            minor = self._ensure_category(store, minor_name, Category.LEVEL_MINOR, major, major_order)
            categories[minor_name] = minor
            for item_order, item_name in enumerate(item_names, start=1):
                item = self._ensure_category(store, item_name, Category.LEVEL_ITEM, minor, item_order)
                categories[item_name] = item
        return categories

    def _ensure_category(self, store, name, level, parent, order):
        category = Category.objects.filter(store=store, name=name, level=level, parent=parent).first()
        if category is None:
            category = Category(store=store, name=name, level=level, parent=parent)
        category.order = order
        category.logo = f"https://dummyimage.com/160x160/f4f7f5/1f5c4a&text={order}"
        category.save()
        return category

    def _ensure_brands(self, store):
        brands = []
        for order, name in enumerate(["创艺优选", "庆勋智造"], start=1):
            brand, _ = Brand.objects.update_or_create(
                store=store,
                name=name,
                defaults={
                    "order": order,
                    "is_active": True,
                    "logo": f"https://dummyimage.com/200x120/1f5c4a/ffffff&text={order}",
                    "description": f"{name} 本地测试品牌",
                },
            )
            brands.append(brand)
        return brands

    def _ensure_products(self, store, categories, brands):
        specs = [
            ("CY-DEMO-001", "创艺嵌入式蒸烤一体机 A8", "蒸烤一体机", 6899, 46, brands[0]),
            ("CY-DEMO-002", "创艺大容量洗碗机 W12", "洗碗机", 5299, 38, brands[0]),
            ("CY-DEMO-003", "庆勋静音中央空调 C3", "中央空调", 12999, 18, brands[1]),
            ("CY-DEMO-004", "创艺全热交换新风 N2", "新风系统", 4599, 25, brands[0]),
            ("CY-DEMO-005", "庆勋智能情景面板 S1", "智能面板", 899, 120, brands[1]),
            ("CY-DEMO-006", "创艺全屋智控套装 Pro", "场景套装", 3699, 35, brands[0]),
            ("CY-DEMO-007", "庆勋嵌入式洗烘组合 W9", "洗碗机", 7699, 22, brands[1]),
            ("CY-DEMO-008", "创艺厨房空气联动套装", "新风系统", 5999, 16, brands[0]),
        ]
        products = []
        sku_count = 0
        for index, (code, name, category_name, price, stock, brand) in enumerate(specs, start=1):
            category = categories[category_name]
            product, _ = Product.objects.update_or_create(
                product_code=code,
                defaults={
                    "store": store,
                    "name": name,
                    "description": f"{name} 的本地测试详情，包含价格、库存、品牌、分类和活动展示关系。",
                    "category": category,
                    "brand": brand,
                    "price": Decimal(price),
                    "dealer_price": Decimal(price) - Decimal("300.00"),
                    "stock": stock,
                    "source": Product.SOURCE_LOCAL,
                    "tag": Product.TAG_BRAND_DIRECT if index % 2 else Product.TAG_SOURCE_FACTORY,
                    "main_images": [f"https://dummyimage.com/800x800/edf5f1/1f5c4a&text=CY-{index:02d}"],
                    "detail_images": [
                        f"https://dummyimage.com/900x600/f8faf9/1f5c4a&text=Detail-{index:02d}-1",
                        f"https://dummyimage.com/900x600/e7efe9/1f5c4a&text=Detail-{index:02d}-2",
                    ],
                    "specifications": {"适用空间": "本地测试", "保修": "三年质保", "安装": "支持上门安装"},
                    "is_active": True,
                    "sales_count": index * 7,
                    "view_count": index * 53,
                },
            )
            products.append(product)
            for sku_index, (sku_name, addon) in enumerate([("标准版", 0), ("尊享版", 600)], start=1):
                sku, _ = ProductSKU.objects.update_or_create(
                    product=product,
                    sku_code=f"{code}-SKU-{sku_index}",
                    defaults={
                        "name": f"{name}-{sku_name}",
                        "specs": {"版本": sku_name, "颜色": "曜石黑" if sku_index == 1 else "月光银"},
                        "price": Decimal(price + addon),
                        "stock": max(stock // 2, 1),
                        "image": f"https://dummyimage.com/800x800/ffffff/1f5c4a&text={code}-{sku_index}",
                        "is_active": True,
                    },
                )
                sku_count += 1
        return products, sku_count

    def _ensure_zones(self, store, products):
        now = timezone.now()
        zones = []
        zone_specs = [
            ("cy-demo-new-arrivals", "新品上新", "本月创艺新品集中展示", 1, products[:5]),
            ("cy-demo-hot-sale", "热销推荐", "适合首页活动卡片和商品排序测试", 2, products[3:8]),
        ]
        for slug, title, subtitle, order, zone_products in zone_specs:
            zone, _ = SpecialZone.objects.update_or_create(
                store=store,
                slug=slug,
                defaults={
                    "title": title,
                    "kind": SpecialZone.KIND_STORE_ACTIVITY,
                    "subtitle": subtitle,
                    "cover_image": f"https://dummyimage.com/900x360/1f5c4a/ffffff&text={slug}",
                    "is_active": True,
                    "show_on_home": True,
                    "home_order": order,
                    "start_at": now - timedelta(days=1),
                    "end_at": now + timedelta(days=60),
                    "description": f"{title} Demo 活动说明",
                    "rules": "用于本地测试，不参与真实营销。",
                },
            )
            for product_order, product in enumerate(zone_products, start=1):
                SpecialZoneProduct.objects.update_or_create(
                    zone=zone,
                    product=product,
                    defaults={"is_active": True, "order": product_order},
                )
            zones.append(zone)
        return zones

    def _ensure_banners(self, store, products, zones):
        banner_specs = [
            ("cy_demo_banner_new_arrivals", "创艺新品上新", products[0], zones[0], 1),
            ("cy_demo_banner_hot_sale", "热销单品推荐", products[2], zones[1], 2),
        ]
        count = 0
        for file_name, title, product, zone, order in banner_specs:
            image = self._ensure_media(file_name, f"demo/{file_name}.jpg")
            banner = HomeBanner.objects.filter(store=store, title=title, position=HomeBanner.POSITION_HOME).first()
            if banner is None:
                banner = HomeBanner(store=store, title=title, position=HomeBanner.POSITION_HOME)
            banner.image = image
            banner.product = product
            banner.special_zone = zone
            banner.order = order
            banner.is_active = True
            banner.save()
            count += 1
        return count

    def _ensure_media(self, original_name, file_path):
        image = MediaImage.objects.filter(original_name=original_name).first()
        if image is None:
            image = MediaImage(original_name=original_name)
        image.file = file_path
        image.content_type = "image/jpeg"
        image.size = 1024
        image.save()
        return image

    def _ensure_home_store_card(self, store, categories, products):
        card = HomeStoreCard.objects.filter(store=store, title="创艺精选店铺卡片").first()
        if card is None:
            card = HomeStoreCard(store=store, title="创艺精选店铺卡片")
        card.subtitle = "平台首页使用的店铺橱窗卡片"
        card.order = 10
        card.is_active = True
        card.save()

        card.card_products.all().delete()
        HomeStoreCardProduct.objects.create(card=card, product=products[0], role=HomeStoreCardProduct.ROLE_MAIN, order=0)
        for order, product in enumerate(products[1:5], start=1):
            HomeStoreCardProduct.objects.create(card=card, product=product, role=HomeStoreCardProduct.ROLE_SECONDARY, order=order)

        card.card_categories.all().delete()
        for order, category_name in enumerate(["厨房电器", "全屋空气", "智能家居"], start=1):
            HomeStoreCardCategory.objects.create(card=card, category=categories[category_name], order=order)
        return card

    def _ensure_customer_groups(self, store, dealer, products):
        group, _ = StoreCustomerGroup.objects.update_or_create(
            store=store,
            name="创艺VIP客户",
            defaults={
                "description": "本地测试客户分组，验证分组价和隐藏分组名称展示逻辑。",
                "status": StoreCustomerGroup.STATUS_ACTIVE,
            },
        )
        StoreCustomerGroupMember.objects.update_or_create(
            store=store,
            user=dealer,
            defaults={"group": group, "phone": dealer.phone or "13900010004", "status": StoreCustomerGroupMember.STATUS_ACTIVE},
        )
        for index, product in enumerate(products[:4], start=1):
            sku = product.skus.order_by("id").first()
            StoreCustomerGroupPrice.objects.update_or_create(
                group=group,
                product=product,
                sku=None,
                defaults={"price": product.price - Decimal(200 + index * 20)},
            )
            if sku:
                StoreCustomerGroupPrice.objects.update_or_create(
                    group=group,
                    product=product,
                    sku=sku,
                    defaults={"price": sku.price - Decimal(260 + index * 20)},
                )
        return group

    def _ensure_discount(self, dealer, products):
        now = timezone.now()
        discount = Discount.objects.filter(name="cy_demo_dealer_discount").first()
        if discount is None:
            discount = Discount(name="cy_demo_dealer_discount")
        discount.discount_type = Discount.TYPE_AMOUNT
        discount.amount = Decimal("150.00")
        discount.effective_time = now - timedelta(days=1)
        discount.expiration_time = now + timedelta(days=60)
        discount.priority = 50
        discount.save()
        for product in products[:3]:
            DiscountTarget.objects.update_or_create(discount=discount, user=dealer, product=product)
        return discount

    def _ensure_order_and_finance(self, store, dealer, products):
        product = products[0]
        sku = product.skus.order_by("id").first()
        quantity = 2
        total = product.price * quantity
        actual = total - Decimal("300.00")
        order, _ = Order.objects.update_or_create(
            order_number="CY-DEMO-ORDER-001",
            defaults={
                "store": store,
                "user": dealer,
                "product": product,
                "quantity": quantity,
                "total_amount": total,
                "discount_amount": Decimal("300.00"),
                "actual_amount": actual,
                "status": "paid",
                "snapshot_contact_name": "创艺经销商",
                "snapshot_phone": dealer.phone or "13900010004",
                "snapshot_address": "安徽省合肥市蜀山区创艺测试小区 1 栋 101",
                "snapshot_province": "安徽省",
                "snapshot_city": "合肥市",
                "snapshot_district": "蜀山区",
                "note": "本地演示订单",
            },
        )
        order.items.all().delete()
        OrderItem.objects.create(
            order=order,
            product=product,
            sku=sku,
            product_name=product.name,
            sku_specs=sku.specs if sku else {},
            sku_code=sku.sku_code if sku else "",
            quantity=quantity,
            unit_price=product.price,
            discount_amount=Decimal("150.00"),
            actual_amount=actual,
            snapshot_image=(product.main_images or [""])[0],
        )

        credit_account, _ = CreditAccount.objects.update_or_create(
            user=dealer,
            defaults={
                "credit_limit": Decimal("50000.00"),
                "payment_term_days": 30,
                "outstanding_debt": actual,
                "is_active": True,
            },
        )
        statement, _ = AccountStatement.objects.update_or_create(
            credit_account=credit_account,
            period_start=date.today().replace(day=1),
            period_end=date.today(),
            defaults={
                "previous_balance": Decimal("0.00"),
                "current_purchases": actual,
                "current_payments": Decimal("0.00"),
                "period_end_balance": actual,
                "due_within_term": actual,
                "status": "draft",
            },
        )
        AccountTransaction.objects.update_or_create(
            credit_account=credit_account,
            order_id=order.id,
            transaction_type="purchase",
            defaults={
                "statement": statement,
                "amount": actual,
                "balance_after": actual,
                "due_date": date.today() + timedelta(days=30),
                "payment_status": "unpaid",
                "description": "创艺 Demo 订单采购",
            },
        )
        return order
