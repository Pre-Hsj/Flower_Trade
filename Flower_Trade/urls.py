"""Flower_Trade URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include

import apps

urlpatterns = [
    path('admin/', admin.site.urls),
    path('carts/', include(('apps.carts.urls', "carts"), namespace='carts')),
    path('order/', include(('apps.order.urls', "order"), namespace='order')),
    path('user/', include(('apps.user.urls', "user"), namespace='user')),
    path('bussiness/', include(('apps.bussiness.urls', "bussiness"), namespace='bussiness')),
    path('public/', include(('apps.public.urls', "public"), namespace='public')),
    path('search/', include('haystack.urls')),
    path('', include(('apps.goods.urls', "goods"), namespace='goods')),


]