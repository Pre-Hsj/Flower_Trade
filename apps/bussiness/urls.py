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
from apps.bussiness import views
from apps.bussiness.views import RegisterView, LoginView, BusCenterView, BusCenterInfoDianView, BusCenterInfoDianChangeView, BusCenterInfoPersonView\
, BusCenterInfoPersonChangeView, BusCenterGoodsSearchView, BusCenterGoodsSearch0View, BusCenterGoodsSearch1View, BusCenterGoodsSearch2View, SelectGoodsSKU, SelectGoodsSKU0, SelectGoodsSKU1, SelectGoodsSKU2\
, BusCenterTypesSearchView, SelectTypesSKU, BusCenterOrderSearch1View, BusCenterOrderSearch2View, BusCenterOrderSearch3View, BusCenterOrderSearch4View,BusCenterOrderSearch5View,\
BusCenterDeleteGoodsView, BusCenterEditGoodsView, BusCenterUploadImageView, BusCenterEditTypesView, BusCenterDeleteTypesView, ActiveView, BusCenterAddTypesView, BusCenterAddGoodsView,\
BusCenterUpdateDianImageView, BusCenterUpdatePersonImageView, BusCenterDataSearch0View, BusCenterDataSearch1View, DataSearchSingle
urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    re_path('active/(?P<token>.*)', views.ActiveView.as_view(), name='active'),
    path('login/', LoginView.as_view(), name='login'),
    path('center/', BusCenterView.as_view(), name='center'),
    re_path('dian/(?P<token>\d+)$', BusCenterInfoDianView.as_view(), name='dian'),
    re_path('dian_change/(?P<token>\d+)$', BusCenterInfoDianChangeView.as_view(), name='dian_change'),
    re_path('person/(?P<token>\d+)$', BusCenterInfoPersonView.as_view(), name='person'),
    re_path('person_change/(?P<token>\d+)$', BusCenterInfoPersonChangeView.as_view(), name='person_change'),
    re_path('goods/(?P<token>\d+)$', BusCenterGoodsSearchView.as_view(), name='goods'),
    re_path('goods0/(?P<token>\d+)$', BusCenterGoodsSearch0View.as_view(), name='goods0'),
    re_path('goods1/(?P<token>\d+)$', BusCenterGoodsSearch1View.as_view(), name='goods1'),
    re_path('goods2/(?P<token>\d+)$', BusCenterGoodsSearch2View.as_view(), name='goods2'),
    re_path('types/(?P<token>\d+)$', BusCenterTypesSearchView.as_view(), name='types'),
    re_path('order1/(?P<token>\d+)/(?P<page>\d+)$', BusCenterOrderSearch1View.as_view(), name='order1'),
    re_path('order2/(?P<token>\d+)/(?P<page>\d+)$', BusCenterOrderSearch2View.as_view(), name='order2'),
    re_path('order3/(?P<token>\d+)/(?P<page>\d+)$', BusCenterOrderSearch3View.as_view(), name='order3'),
    re_path('order4/(?P<token>\d+)/(?P<page>\d+)$', BusCenterOrderSearch4View.as_view(), name='order4'),
    re_path('order5/(?P<token>\d+)/(?P<page>\d+)$', BusCenterOrderSearch5View.as_view(), name='order5'),
    path('deletegoods/', BusCenterDeleteGoodsView.as_view(), name='deletegoods'),
    path('deletetypes/', BusCenterDeleteTypesView.as_view(), name='deletetypes'),
    path('editgoods/', BusCenterEditGoodsView.as_view(), name='editgoods'),
    path('edittypes/', BusCenterEditTypesView.as_view(), name='edittypes'),
    path('upload/', BusCenterUploadImageView.as_view(), name='upload'),
    re_path('active/(?P<token>.*)', views.ActiveView.as_view(), name='active'),
    path('addtypes/',BusCenterAddTypesView.as_view(),name='addtypes'),
    path('addgoods/',BusCenterAddGoodsView.as_view(),name='addgoods'),
    path('updatedianimage/',BusCenterUpdateDianImageView.as_view(),name='updatedianimage'),
    path('updatepersonimage/',BusCenterUpdatePersonImageView.as_view(),name='updatepersonimage'),
    re_path('selectgoodssku/(?P<token>\d+)$', SelectGoodsSKU),
    re_path('selectgoodssku0/(?P<token>\d+)$', SelectGoodsSKU0),
    re_path('selectgoodssku1/(?P<token>\d+)$', SelectGoodsSKU1),
    re_path('selectgoodssku2/(?P<token>\d+)$', SelectGoodsSKU2),
    re_path('selecttypessku/(?P<token>\d+)$', SelectTypesSKU),
    re_path('datasearch0/(?P<token>\d+)$', BusCenterDataSearch0View.as_view(), name='datasearch0'),
    re_path('datasearch1/(?P<token>\d+)$', BusCenterDataSearch1View.as_view(), name='datasearch1'),
    re_path('datasearchsingle/(?P<token>\d+)$', DataSearchSingle),

]
