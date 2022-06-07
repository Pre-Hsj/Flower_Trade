# Generated by Django 2.0 on 2022-04-02 11:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('goods', '0004_goodstype_banners'),
    ]

    operations = [
        migrations.AddField(
            model_name='goods',
            name='business',
            field=models.CharField(default='', max_length=10, verbose_name='商家id'),
        ),
        migrations.AddField(
            model_name='goodssku',
            name='business',
            field=models.CharField(default='', max_length=10, verbose_name='商家id'),
        ),
        migrations.AlterField(
            model_name='goodssku',
            name='status',
            field=models.SmallIntegerField(choices=[(0, '下架'), (1, '上架'), (2, '待上架')], default=1, verbose_name='商品状态'),
        ),
    ]