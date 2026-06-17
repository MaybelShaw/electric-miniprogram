from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0040_product_specifications"),
        ("stores", "0003_alter_store_options_alter_storemember_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="specialzone",
            name="description",
            field=models.TextField(blank=True, default="", verbose_name="活动说明"),
        ),
        migrations.AddField(
            model_name="specialzone",
            name="rules",
            field=models.TextField(blank=True, default="", verbose_name="活动规则"),
        ),
        migrations.AlterField(
            model_name="specialzone",
            name="kind",
            field=models.CharField(
                choices=[
                    ("platform_activity", "平台活动"),
                    ("store_activity", "店铺活动"),
                    ("activity", "活动专区"),
                    ("promotion", "优惠专区"),
                    ("category", "品类专区"),
                    ("brand", "品牌专区"),
                    ("custom", "自定义专区"),
                ],
                default="activity",
                max_length=20,
                verbose_name="专区类型",
            ),
        ),
        migrations.CreateModel(
            name="HomeStoreCard",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("title", models.CharField(max_length=100, verbose_name="卡片标题")),
                ("subtitle", models.CharField(blank=True, default="", max_length=200, verbose_name="卡片副标题")),
                ("order", models.IntegerField(default=0, verbose_name="首页排序")),
                ("is_active", models.BooleanField(default=True, verbose_name="是否启用")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="更新时间")),
                ("store", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="home_store_cards", to="stores.store", verbose_name="店铺")),
            ],
            options={
                "verbose_name": "首页店铺卡片",
                "verbose_name_plural": "首页店铺卡片",
                "ordering": ["order", "id"],
            },
        ),
        migrations.CreateModel(
            name="HomeStoreCardProduct",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("role", models.CharField(choices=[("main", "主推商品"), ("secondary", "副推商品")], max_length=20, verbose_name="商品角色")),
                ("order", models.IntegerField(default=0, verbose_name="排序")),
                ("card", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="card_products", to="catalog.homestorecard", verbose_name="首页店铺卡片")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="home_store_card_links", to="catalog.product", verbose_name="商品")),
            ],
            options={
                "verbose_name": "首页店铺卡片商品",
                "verbose_name_plural": "首页店铺卡片商品",
                "ordering": ["role", "order", "id"],
            },
        ),
        migrations.CreateModel(
            name="HomeStoreCardCategory",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("order", models.IntegerField(default=0, verbose_name="排序")),
                ("card", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="card_categories", to="catalog.homestorecard", verbose_name="首页店铺卡片")),
                ("category", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="home_store_card_links", to="catalog.category", verbose_name="一级分类")),
            ],
            options={
                "verbose_name": "首页店铺卡片分类",
                "verbose_name_plural": "首页店铺卡片分类",
                "ordering": ["order", "id"],
            },
        ),
        migrations.AddIndex(
            model_name="homestorecard",
            index=models.Index(fields=["is_active", "order"], name="catalog_hom_is_acti_ef9863_idx"),
        ),
        migrations.AddIndex(
            model_name="homestorecard",
            index=models.Index(fields=["store", "is_active"], name="catalog_hom_store_i_d88269_idx"),
        ),
        migrations.AddConstraint(
            model_name="homestorecardproduct",
            constraint=models.UniqueConstraint(fields=("card", "product"), name="unique_home_store_card_product"),
        ),
        migrations.AddConstraint(
            model_name="homestorecardcategory",
            constraint=models.UniqueConstraint(fields=("card", "category"), name="unique_home_store_card_category"),
        ),
    ]
