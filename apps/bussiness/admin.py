from django.contrib import admin
from .models import Bussiness
# Register your models here.
from ..goods.admin import BaseModelAdmin


class BussinessAdmin(BaseModelAdmin):
    pass

admin.site.register(Bussiness, BussinessAdmin)
admin.site.site_header="创客花店后台管理系统"
admin.site.site_title="创客花店后台管理系统"