# Generated by Django 5.1 on 2024-10-27 19:30

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Queue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(max_length=100)),
                ('estimated_wait_time_per_turn', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_closed', models.BooleanField(default=False)),
                ('status', models.CharField(choices=[('normal', 'Normal'), ('busy', 'Busy'), ('full', 'Full')], default='normal', max_length=10)),
                ('category', models.CharField(choices=[('restaurant', 'Restaurant'), ('general', 'General'), ('hospital', 'Hospital'), ('bank', 'Bank'), ('service center', 'Service center')], max_length=20)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='queue_logos/')),
                ('capacity', models.PositiveIntegerField()),
                ('completed_participants_count', models.PositiveIntegerField(default=0)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Participant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('joined_at', models.DateTimeField(null=True)),
                ('position', models.PositiveIntegerField(null=True)),
                ('queue_code', models.CharField(editable=False, max_length=6, unique=True)),
                ('user', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('queue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='queue_manager.queue')),
            ],
            options={
                'unique_together': {('user', 'queue')},
            },
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_read', models.BooleanField(default=False)),
                ('participant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='queue_manager.participant')),
                ('queue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='queue_manager.queue')),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_type', models.CharField(choices=[('creator', 'Queue Creator'), ('participant', 'Participant')], max_length=20)),
                ('phone_no', models.CharField(max_length=15)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
