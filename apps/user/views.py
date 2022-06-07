import re

from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect
from django.views.generic import View
from django.core.paginator import Paginator
# Create your views here.
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from django.conf import settings
from django.core.mail import send_mail
from redis import StrictRedis
from django_redis import get_redis_connection
from utils.mixin import LoginRequiredMixin
from apps.user.models import User, Address
from apps.goods.models import GoodsSKU, GoodsType
from apps.order.models import OrderGoods,OrderInfo
from celery_tasks.tasks import send_register_active_email
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired


class RegisterView(View):
    """注册"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request):
        """显示注册页面"""
        return render(request, 'register.html')

    def post(self, request):
        """进行注册处理"""
        # 接收数据
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 进行数据校验
        if not all([username, password, email]):
            # 数据不完整
            return render(request, 'register.html', {'errmsg': '数据不完整'})
        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})

        # 校验用户名是否重复
        try:
            # 用户名已存在
            User.objects.get(username=username)
            return render(request, 'register.html', {'errmsg': '用户名已存在'})
        except User.DoesNotExist:
            # 用户名不存在
            # 进行业务处理：进行用户注册
            user = User.objects.create_user(username, email, password)
            user.is_active = 0
            user.save()

            # 发送激活邮件，包含激活链接: http://127.0.0.1:8000/user/active/3
            # 激活链接中需要包含用户的身份信息,并且要把身份信息加密
            # 加密用户的身份信息，生成激活token
            serializer = Serializer(settings.SECRET_KEY, 3600)
            info = {'confirm': user.id}
            token = serializer.dumps(info)
            token = token.decode()

            # 发邮件
            send_register_active_email.delay(email, username, token)

            # 返回应答,跳转到首页
            return redirect(reverse('goods:index'))


class ActiveView(View):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, token):
        """用户激活"""
        # 进行解密，获取要激活的用户信息
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            # 获取待激活用户的id
            user_id = info['confirm']

            # 根据id获取用户信息
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()

            # 返回应答，跳转至登录页面

            return redirect(reverse('user:login'))
        except SignatureExpired as e:
            return HttpResponse('激活链接已过期')


class LoginView(View):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    """登录"""

    def get(self, request):
        # 判断是否记住了用户名
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ""
            checked = ''

        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        """接收数据"""
        username = request.POST.get('username')
        password = request.POST.get('pwd')
        """校验数据"""
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '数据不完整'})
        else:
            # 业务处理:登录校验
            user = authenticate(username=username, password=password)
            if user is not None:
                # 用户名密码正确
                if user.is_active:
                    # 用户已激活
                    # 记录用户的登录状态,将user附加到session中
                    login(request, user)
                    next_url = request.POST.get('next')
                    if next_url:
                        next1 = next_url
                    else:
                        next1 = reverse('goods:index')
                    # 获取登录后所要跳转到的地址
                    print(1)
                    # next_url = request.POST.get('next', reverse('goods:index'))
                    print(next1)

                    response = redirect(next1)
                    # 判断是否需要记录用户名
                    remember = request.POST.get('remember')
                    if remember == 'on':
                        # 记住用户名
                        response.set_cookie('username', username, max_age=7 * 24 * 3600)
                    else:
                        response.delete_cookie('username')

                    return response
                else:
                    # 用户未激活
                    return render(request, 'login.html', {'errmsg': '账户未激活'})
            else:
                # 用户名或密码错误
                return render(request, 'login.html', {'errmsg': '用户名或密码错误'})


class LogoutView(View):
    '''退出登录'''

    def get(self, request):
        logout(request)
        return redirect(reverse('goods:index'))


class UserInfoView(LoginRequiredMixin, View):
    """用户中心信息页"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request):
        # Django 会给request对象添加一个属性request.user
        # 如果用户未登录->user是AnonymousUser类的一个实例
        # 如果用户登录->user是User类的一个实例

        # 获取用户的个人信息
        user = request.user
        address = Address.objects.filter(user=user)
        # 获取商品分类信息
        types = GoodsType.objects.all()

        # 获取用户的历史浏览记录
        # 1.什么时候添加历史浏览记录：访问商品的详情页面的时候添加历史浏览记录
        # 2.什么时候获取历史浏览记录：访问用户中心个人信息页的时候需要获取历史浏览记录
        # 3.历史浏览记录需要存储在哪里：redis数据库（内存型数据库）
        # 4.redis存储历史浏览记录的格式：string，hash，list，set，zset（）
        # 所有用户的历史浏览记录用一条数据保存 hash history: user_用户_id:'1,2,3'
        # 每个用户的历史浏览记录用一条数据保存 list history_用户id:[3,2,1] 添加历史浏览记录的时候，用户最新浏览的商品id从列表左侧插入
        # sr = StrictRedis(host='127.0.0.1', port=6379, db=2)
        con = get_redis_connection('default')
        history_key = 'history_%d' % user.id

        # 获取用户最新浏览的5条历史记录
        sku_ids = con.lrange(history_key, 0, 4)

        # 从数据库中查询用户浏览的商品的具体信息
        # goods_li = GoodsSKU.objects.filter(id__in=sku_ids)
        # goods_res = []
        # for a_id in sku_ids:
        #     for goods in goods_li:
        #         if a_id == goods.id:
        #             goods_res.append(goods)
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)
        # 组织上下文
        context = {'page': 'user',
                   'address': address,
                   'goods_li': goods_li,
                   'types':types}

        # 除了本人传给模板文件的模板变量之外，Django会把request.user一同传给模板对象（此处指的是用login登录之后）
        return render(request, 'user_center_info.html', context)


class UserOrderView(LoginRequiredMixin, View):
    """用户中心信息页"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request,page):
        # 获取用户的订单信息
        user = request.user
        orders = OrderInfo.objects.filter(user=user)
        # 获取商品分类信息
        types = GoodsType.objects.all()
        for order in orders:
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)
            for order_sku in order_skus:
                amount = order_sku.count*order_sku.price
                order_sku.amount = amount
            order.order_skus = order_skus
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
        paginator = Paginator(orders, 5)

        # 获取第page页的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1

        # 获取第page页的page实例对象
        order_page = paginator.page(page)

        contex = {
            'order_page': order_page,
            'page': 'order',
            'types':types,
        }
        return render(request, 'user_center_order.html', contex)


class AddressView(LoginRequiredMixin, View):
    """用户中心信息页"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request):
        """显示"""
        # 获取登录用户对应的User对象
        user = request.user
        # 获取用户的默认收货地址
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     # 不存在默认收货地址
        #     address = None

        address = Address.objects.filter(user=user)
        # 获取商品分类信息
        types = GoodsType.objects.all()
        return render(request, 'user_center_site.html', {'page': 'address','types': types, 'address': address})

    def post(self, request):
        """地址的添加"""
        # 接收数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        # 校验数据
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg': '数据不完整'})
        else:
            if not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
                return render(request, 'user_center_site.html', {'errmsg': '手机格式不正确'})
            else:
                # 如果用户已存在默认收货地址，添加的地址不作为默认收货地址，否则作为默认收货地址
                user = request.user
                # try:
                #     address = Address.objects.get(user=user, is_default=True)
                # except Address.DoesNotExist:
                #     # 不存在默认收货地址
                #     address = None
                try:
                    address = Address.objects.get(user=user, is_default=1)
                    is_default = False
                except:
                    is_default = True
                # 添加地址
                Address.objects.create(user=user,
                                       addr=addr,
                                       receiver=receiver,
                                       zip_code=zip_code,
                                       phone=phone,
                                       is_default=is_default)
                return redirect(reverse('user:address'))


class UserHistoryView(LoginRequiredMixin, View):
    """用户历史浏览记录信息页"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request):
        # Django 会给request对象添加一个属性request.user
        # 如果用户未登录->user是AnonymousUser类的一个实例
        # 如果用户登录->user是User类的一个实例

        # 获取用户的个人信息
        user = request.user
        # 获取用户的历史浏览记录
        # 1.什么时候添加历史浏览记录：访问商品的详情页面的时候添加历史浏览记录
        # 2.什么时候获取历史浏览记录：访问用户中心个人信息页的时候需要获取历史浏览记录
        # 3.历史浏览记录需要存储在哪里：redis数据库（内存型数据库）
        # 4.redis存储历史浏览记录的格式：string，hash，list，set，zset（）
        # 所有用户的历史浏览记录用一条数据保存 hash history: user_用户_id:'1,2,3'
        # 每个用户的历史浏览记录用一条数据保存 list history_用户id:[3,2,1] 添加历史浏览记录的时候，用户最新浏览的商品id从列表左侧插入
        # sr = StrictRedis(host='127.0.0.1', port=6379, db=2)
        con = get_redis_connection('default')
        # 获取商品分类信息
        types = GoodsType.objects.all()
        history_key = 'history_%d' % user.id

        # 获取用户最新浏览的5条历史记录
        sku_ids = con.lrange(history_key, 0, 4)

        # 从数据库中查询用户浏览的商品的具体信息
        # goods_li = GoodsSKU.objects.filter(id__in=sku_ids)
        # goods_res = []
        # for a_id in sku_ids:
        #     for goods in goods_li:
        #         if a_id == goods.id:
        #             goods_res.append(goods)
        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)
        # 组织上下文
        context = {'page': 'history',
                   'goods_li': goods_li,
                   'types':types}

        # 除了本人传给模板文件的模板变量之外，Django会把request.user一同传给模板对象（此处指的是用login登录之后）
        return render(request, 'user_center_history.html', context)

class DeleteAddressView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request):
        try:
            ID = request.GET.get('id')
            Address.objects.get(id=ID).delete()
            #resultdict = {}
            #resultdict['status'] = 200
            dict = {}
            dict['src'] = "None"
            data = {"code": 200, "msg": "1", "data": dict}
            return JsonResponse(data)
        except:
            dict = {}
            dict['src'] = "None"
            data = {"code": 0, "msg": "1", "data": dict}
            return JsonResponse(data)

class SetDefaultAddressView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request):
        try:
            id = request.GET.get('id')# 地址id
            ID = request.GET.get('ID')# 用户ID

            # 查询现有的默认地址id
            default = Address.objects.get(user_id=ID, is_default=1)
            print(default.id)
            print(id)
            if(int(default.id) == int(id)):
                print('两个ID是一样的')
                # 说明两个地址是一样的
                dict = {}
                dict['src'] = "None"
                data = {"code": 100, "msg": "1", "data": dict}
                return JsonResponse(data)
            # 两个地址不同
            default.is_default=0
            default.save()
            new_default = Address.objects.get(id=id)
            new_default.is_default=1
            new_default.save()
            dict = {}
            dict['src'] = "None"
            data = {"code": 200, "msg": "1", "data": dict}
            return JsonResponse(data)
        except:
            dict = {}
            dict['src'] = "None"
            data = {"code": 0, "msg": "1", "data": dict}
            return JsonResponse(data)

class EditAddressView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def post(self, request):
        try:
            id = request.POST.get('id')
            receiver = request.POST.get('receiver')
            addr = request.POST.get('addr')
            phone = request.POST.get('phone')

            # 查找对应的id
            address = Address.objects.get(id=id)
            address.receiver=receiver
            address.addr=addr
            address.phone=phone
            address.save()

            dict={}
            dict['src'] = "None"
            data = {"code": 200, "msg": "1", "data": dict}
            return JsonResponse(data)
        except:
            dict = {}
            dict['src'] = "None"
            data = {"code": 0, "msg": "1", "data": dict}
            return JsonResponse(data)