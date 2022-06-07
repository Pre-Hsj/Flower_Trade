from django.contrib import admin

# Register your models here.
from apps.goods.admin import BaseModelAdmin
from apps.user.models import User


class UserAdmin(BaseModelAdmin):
    pass

admin.site.register(User, UserAdmin)