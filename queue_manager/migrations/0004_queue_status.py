# Generated by Django 5.1 on 2024-10-22 08:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('queue_manager', '0003_queue_is_closed_alter_participant_position'),
    ]

    operations = [
        migrations.AddField(
            model_name='queue',
            name='status',
            field=models.CharField(choices=[('open', 'Open'), ('busy', 'Busy'), ('full', 'Full'), ('closed', 'Closed')], default='open', max_length=10),
        ),
    ]
