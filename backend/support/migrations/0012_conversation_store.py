from django.db import migrations, models
import django.db.models.deletion


def set_main_store(apps, schema_editor):
    Store = apps.get_model("stores", "Store")
    SupportConversation = apps.get_model("support", "SupportConversation")
    store = Store.objects.filter(is_main=True).order_by("id").first() or Store.objects.order_by("id").first()
    if store:
        SupportConversation.objects.filter(store__isnull=True).update(store_id=store.id)


class Migration(migrations.Migration):
    dependencies = [
        ("stores", "0004_store_sub_admin_permissions"),
        ("support", "0011_feedback_ticket"),
    ]

    operations = [
        migrations.AddField(
            model_name="supportconversation",
            name="store",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="support_conversations",
                to="stores.store",
                verbose_name="店铺",
            ),
        ),
        migrations.RunPython(set_main_store, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="supportconversation",
            name="store",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="support_conversations",
                to="stores.store",
                verbose_name="店铺",
            ),
        ),
        migrations.AddIndex(
            model_name="supportconversation",
            index=models.Index(fields=["user", "store"], name="support_conv_user_store_idx"),
        ),
        migrations.AddIndex(
            model_name="supportconversation",
            index=models.Index(fields=["store", "updated_at"], name="support_conv_store_updated_idx"),
        ),
    ]
