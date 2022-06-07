import re

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import View

from apps.bussiness.models import Bussiness
from apps.public.models import Public, Feedback


class NoticeView(View):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request):
        """获取公告"""
        notices = Public.objects.all()
        contex = {
            'notices': notices,
        }
        return render(request, 'notice.html', contex)

    def post(self, request):
        pass


class FeedbackView(View):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request,token):
        """获取反馈页面"""
        business = Bussiness.objects.get(id=token)
        contex = {
            'business': business,
        }
        return render(request, 'feedback.html', contex)

    def post(self, request, token):
        feedbackContent = request.POST.get('feedbackContent')
        business = Bussiness.objects.get(id=token)

        # 进行数据校验
        if not all([feedbackContent, business]):
            # 数据不完整
            contex = {
                 'business': business,
                'errmsg': '数据不完整'
            }
            return render(request, 'feedback.html', contex)

        feedback = Feedback.objects.create(business=business,feedbackContent=feedbackContent)
        feedback.save()
        contex = {
            'business': business,
            'errmsg': '反馈成功'
        }
        return render(request, 'feedback.html', contex)


class FeedbackHistoryView(View):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request,token):
        """获取反馈页面"""
        business = Bussiness.objects.get(id=token)
        feedback = Feedback.objects.filter(business=business)
        contex = {
            'business': business,
            'feedback': feedback,
        }
        return render(request, 'feedbackHistory.html', contex)

    def post(self, request, token):
        pass



def selectFeedbackHistory(requst, token):
    business = Bussiness.objects.get(id=token)
    feedback = Feedback.objects.filter(business=business)
    total = feedback.count()
    resultdict = {}
    resultdict['total'] = total
    dict = []
    for p in feedback:
        dic = {}
        dic['id'] = p.id
        dic['create_time'] = p.create_time
        dic['feedbackContent'] = p.feedbackContent
        dic['feedbackAnswer'] = p.feedbackAnswer
        dict.append(dic)
    resultdict['code'] = 0
    resultdict['msg'] = "1"
    resultdict['count'] = total
    resultdict['data'] = dict
    print(resultdict)
    return JsonResponse(resultdict)