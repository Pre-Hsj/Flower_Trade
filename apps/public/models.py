from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import AbstractUser

from apps import bussiness
from db.base_model import BaseModel
from apps.bussiness.models import Bussiness
# Create your models here.



class Public(BaseModel):
    '''公告模型类'''
    publicNumber = models.CharField(max_length=36, verbose_name='公告编号')
    publicTitle = models.CharField(max_length=256, verbose_name='公告标题')
    publicContent = models.TextField(verbose_name='公告内容')

    class Meta:
        db_table = 'df_public'
        verbose_name = '公告表'
        verbose_name_plural = verbose_name


class Feedback(BaseModel):
    """反馈模型类"""
    business = models.ForeignKey('bussiness.Bussiness', verbose_name='所属商家', on_delete=models.CASCADE)
    feedbackContent = models.TextField(verbose_name='反馈问题')
    feedbackAnswer = models.TextField(default="",verbose_name='内容')
    class Meta:
        db_table = 'df_feedback'
        verbose_name = '反馈表'
        verbose_name_plural = verbose_name