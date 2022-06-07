from django.contrib import admin

# Register your models here.
from apps.goods.admin import BaseModelAdmin
from apps.public.models import Public, Feedback


class PublicAdmin(BaseModelAdmin):
    pass

class FeedbackAdmin(BaseModelAdmin):
    pass


admin.site.register(Public, PublicAdmin)
admin.site.register(Feedback, FeedbackAdmin)
