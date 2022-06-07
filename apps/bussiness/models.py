from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
from db.base_model import BaseModel



class Bussiness(BaseModel):
    '''商家模型类'''

    name = models.CharField(max_length=80, verbose_name='店铺名称')
    password = models.CharField(max_length=256, verbose_name='密码')
    addr = models.CharField(max_length=256, default='无', verbose_name='店铺地址')
    email = models.CharField(max_length=56, default='无', verbose_name='邮箱地址')
    signature = models.CharField(max_length=256, default='无', verbose_name='店铺宣言')
    is_active = models.BooleanField(default=0, verbose_name='是否激活')
    kinds = models.CharField(max_length=256,default='无',verbose_name="店铺经营种类")
    emailRemind = models.CharField(max_length=5,default="否",verbose_name='邮件提醒')
    image = models.ImageField(upload_to='dian', default='group1/M00/00/01/rB58N2JIAz6AEi9rAAIlyVsSju03648559', verbose_name='图片路径')
    accountRelate = models.CharField(max_length=30, default='无',verbose_name='账号关联')
    personName = models.CharField(max_length=30,default='无',verbose_name='联系人姓名')
    personAge = models.CharField(max_length=10,default='无',verbose_name='联系人年龄')
    personSex = models.CharField(max_length=10, default='无',verbose_name='联系人性别')
    personAddr = models.CharField(max_length=256, default='无', verbose_name='联系人地址')
    personEmail = models.CharField(max_length=56, default='无', verbose_name='邮箱地址')
    personEmailRemind = models.CharField(max_length=5, default="否", verbose_name='联系人邮件提醒')
    personDate = models.CharField(max_length=50,default="无",verbose_name="联系人生日")
    personDescription = models.CharField(max_length=256,default='无',verbose_name='联系人信息描述')
    personAccountRelate = models.CharField(max_length=30, default='无', verbose_name='联系人账号关联')
    personImage = models.ImageField(upload_to='dian_person', default='group1/M00/00/01/rB58N2JIAz6AEi9rAAIlyVsSju03648559', verbose_name='图片路径')


    class Meta:
        db_table = 'df_bussiness'
        verbose_name = '商家'
        verbose_name_plural = verbose_name