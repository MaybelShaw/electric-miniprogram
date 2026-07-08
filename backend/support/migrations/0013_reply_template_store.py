from django.db import migrations, models
import django.db.models.deletion


def set_main_store(apps, schema_editor):
    Store = apps.get_model("stores", "Store")
    SupportReplyTemplate = apps.get_model("support", "SupportReplyTemplate")
    store = Store.objects.filter(is_main=True).order_by("id").first() or Store.objects.order_by("id").first()
    if store:
        SupportReplyTemplate.objects.filter(store__isnull=True).update(store_id=store.id)


class Migration(migrations.Migration):
    dependencies = [
        ("support", "0012_conversation_store"),
    ]

    operations = [
        migrations.AddField(
            model_name="supportreplytemplate",
            name="store",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="support_reply_templates",
                to="stores.store",
                verbose_name="店铺",
            ),
        ),
        migrations.RunPython(set_main_store, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="supportreplytemplate",
            name="store",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="support_reply_templates",
                to="stores.store",
                verbose_name="店铺",
            ),
        ),
        migrations.AddIndex(
            model_name="supportreplytemplate",
            index=models.Index(fields=["store", "template_type", "enabled"], name="support_tpl_store_type_idx"),
        ),
    ]
