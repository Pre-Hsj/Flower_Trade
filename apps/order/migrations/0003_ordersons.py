# Generated by Django 2.0 on 2022-04-06 01:11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bussiness', '0006_bussiness_persondate'),
        ('order', '0002_auto_20220130_2058'),
    ]

    operations = [
        migrations.CreateModel(
            name='OrderSons',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create_time', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('is_delete', models.BooleanField(default=False, verbose_name='删除标记')),
                ('bussiness', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='bussiness.Bussiness', verbose_name='商家ID')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='order.OrderInfo', verbose_name='订单')),
            ],
            options={
                'verbose_name': '子订单表',
                'verbose_name_plural': '子订单表',
                'db_table': 'df_order_sons',
            },
        ),
    ]
