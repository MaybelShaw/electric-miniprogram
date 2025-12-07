from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('support', '0003_supportmessage_order_supportmessage_product_and_more'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='supportmessage',
            name='support_sup_ticket__8eea9f_idx',
        ),
        migrations.RemoveIndex(
            model_name='supportticket',
            name='support_sup_status_c35d7c_idx',
        ),
        migrations.RemoveIndex(
            model_name='supportticket',
            name='support_sup_priorit_049754_idx',
        ),
        migrations.RemoveIndex(
            model_name='supportticket',
            name='support_sup_user_id_2e68d8_idx',
        ),
        migrations.RenameModel(
            old_name='SupportTicket',
            new_name='SupportConversation',
        ),
        migrations.RenameField(
            model_name='supportmessage',
            old_name='ticket',
            new_name='conversation',
        ),
        migrations.RemoveField(
            model_name='supportconversation',
            name='assigned_to',
        ),
        migrations.RemoveField(
            model_name='supportconversation',
            name='order',
        ),
        migrations.RemoveField(
            model_name='supportconversation',
            name='priority',
        ),
        migrations.RemoveField(
            model_name='supportconversation',
            name='status',
        ),
        migrations.RemoveField(
            model_name='supportconversation',
            name='subject',
        ),
        migrations.AddIndex(
            model_name='supportconversation',
            index=models.Index(fields=['user'], name='support_conv_user_idx'),
        ),
        migrations.AddIndex(
            model_name='supportconversation',
            index=models.Index(fields=['updated_at'], name='support_conv_updated_idx'),
        ),
        migrations.AddIndex(
            model_name='supportmessage',
            index=models.Index(fields=['conversation', 'created_at'], name='support_msg_conv_created_idx'),
        ),
    ]
