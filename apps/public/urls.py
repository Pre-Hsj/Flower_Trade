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
from .views import NoticeView, FeedbackView, FeedbackHistoryView, selectFeedbackHistory
import apps

urlpatterns = [
    # path('register/', views.register),
    path('notice/', NoticeView.as_view(), name='notice'),
    re_path('feedback/(?P<token>\d+)$', FeedbackView.as_view(), name='feedback'),
    re_path('feedbackHistory/(?P<token>\d+)$', FeedbackHistoryView.as_view(), name='history'),
    re_path('selectfeedbackhistory/(?P<token>\d+)$', selectFeedbackHistory),
]
