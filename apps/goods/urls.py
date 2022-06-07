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
from django.urls import path, re_path

import apps
from apps import user, carts, order, goods
from django.conf.urls import url

from apps.goods import views
from apps.goods.views import IndexView, DetailView, ListView

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    re_path('goods/(?P<goods_id>\d+)$', DetailView.as_view(), name='detail'),
    re_path('list/(?P<type_id>\d+)/(?P<page>\d+)$', ListView.as_view(), name='list'),
]
