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
from django.urls import path, include, re_path
from . import views
from django.contrib.auth.decorators import login_required
from .views import RegisterView, DeleteAddressView, SetDefaultAddressView,EditAddressView
import apps

urlpatterns = [
    # path('register/', views.register),
    path('register/', views.RegisterView.as_view(), name='register'),
    re_path('active/(?P<token>.*)', views.ActiveView.as_view(), name='active'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('info/', views.UserInfoView.as_view(), name='user'),
    re_path('order/(?P<page>\d+)$', views.UserOrderView.as_view(), name='order'),
    path('address/', views.AddressView.as_view(), name='address'),
    path('history/', views.UserHistoryView.as_view(), name='history'),
    path('deleteaddress/',DeleteAddressView.as_view(),name='deleteaddress'),
    path('setdefaultaddress/',SetDefaultAddressView.as_view(),name='setdefaultaddress'),
    path('editaddress/', EditAddressView.as_view(),name='editaddress')
    ]
