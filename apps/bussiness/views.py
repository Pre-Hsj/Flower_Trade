import json
import re

from django.core import paginator
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import View
from django.http import JsonResponse, HttpResponse
from django_redis import get_redis_connection
from fdfs_client.client import get_tracker_conf, Fdfs_client
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired

from apps.goods.models import GoodsSKU, Goods
from apps.order.models import OrderSons, OrderInfo, OrderGoods
from celery_tasks.tasks import send_register_active_email_business
from Flower_Trade import settings
from apps.bussiness.models import Bussiness
from utils.mixin import LoginRequiredMixin


def kindChange1(flag, name):
    if flag == 'on':
        return name
    else:
        return "None"


def emailChange(flag):
    if flag == 'on':
        return "是"
    else:
        return "否"


def sexChange(flag):
    if flag == 1:
        return "女"
    else:
        return "男"


class RegisterView(View):
    """注册"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request):
        """显示注册页面"""
        return render(request, 'register_bussiness.html')

    def post(self, request):
        """进行注册处理"""
        # 接收数据
        business_name = request.POST.get('business_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # 进行数据校验
        if not all([business_name, password, email]):
            # 数据不完整
            return render(request, 'register_bussiness.html', {'errmsg': '数据不完整'})
        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register_bussiness.html', {'errmsg': '邮箱格式不正确'})

        if allow != 'on':
            return render(request, 'register_bussiness.html', {'errmsg': '请同意协议'})

        # 校验用户名是否重复
        try:
            # 用户名已存在
            Bussiness.objects.get(name=business_name)
            return render(request, 'register_bussiness.html', {'errmsg': '用户名已存在'})
        except Bussiness.DoesNotExist:
            # 用户名不存在
            # 进行业务处理：进行用户注册
            bussiness = Bussiness.objects.create(name=business_name, email=email, password=password)
            bussiness.save()

            # 发送激活邮件，包含激活链接: http://127.0.0.1:8000/user/active/3
            # 激活链接中需要包含用户的身份信息,并且要把身份信息加密
            # 加密用户的身份信息，生成激活token
            serializer = Serializer(settings.SECRET_KEY, 3600)
            info = {'confirm': bussiness.id}
            token = serializer.dumps(info)
            token = token.decode()

            # 发邮件
            send_register_active_email_business.delay(email, business_name, token)

            # 返回应答,跳转到首页
            return redirect(reverse('goods:index'))


class LoginView(View):
    """登录"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request):
        """显示登录页面"""
        return render(request, 'login_business.html')

    def post(self, request):
        """接收数据"""
        business_name = request.POST.get('business_name')
        password = request.POST.get('pwd')
        """校验数据"""
        if not all([business_name, password]):
            return render(request, 'login_business.html', {'errmsg': '数据不完整'})
        else:
            # 业务处理:登录校验
            business = Bussiness.objects.get(name=business_name, password=password)
            if business:
                request.session['business_name'] = business_name

                # 存在该business用户
                if business.is_active:
                    next_url = request.POST.get('next')
                    if next_url:
                        next1 = next_url
                    else:
                        next1 = reverse('goods:index')
                    # 获取登录后所要跳转到的地址
                    # next_url = request.POST.get('next', reverse('goods:index'))
                    print(next1)

                    response = redirect(next1)
                    # 判断是否需要记录用户名
                    remember = request.POST.get('remember')
                    if remember == 'on':
                        # 记住用户名
                        response.set_cookie('business_name', business_name, max_age=7 * 24 * 3600)
                    else:
                        response.delete_cookie('business_name')

                    goods = Goods.objects.filter(business=business.id)
                    contex = {
                        'business': business,
                        'response': response,
                        'goods': goods,
                    }
                    return render(request, 'bus_center.html', contex)
                else:
                    # 用户未激活
                    return render(request, 'login_business.html', {'errmsg': '账户未激活'})
            else:
                # 用户名或密码错误
                return render(request, 'login_business.html', {'errmsg': '用户名或密码错误'})


class BusCenterView(View):
    """用户中心"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request):
        """用户中心"""
        return render(request, 'bus_center.html')


class BusCenterInfoDianView(View):
    """用户中心"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, token):
        """用户中心"""
        business = Bussiness.objects.get(id=token)
        contex = {
            'business': business,
        }
        return render(request, 'bus_center_info_dian.html', contex)


class BusCenterInfoDianChangeView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, token):
        """店铺信息"""
        business = Bussiness.objects.get(id=token)
        contex = {
            'business': business,
        }
        return render(request, 'bus_center_info_dian_change.html', contex)

    def post(self, request, token):
        """店铺信息修改"""
        # 1.获取请求中传递过来的信息
        businessName = request.POST.get('business_name')
        businessEmail = request.POST.get('business_email')
        businessAddr = request.POST.get('interest')
        businessRemind = emailChange(request.POST.get('business_remind'))
        businessSignature = request.POST.get('business_signature')

        Fresh = kindChange1(request.POST.get('like[Fresh]'), "鲜切花")
        Fake = kindChange1(request.POST.get('like[Fake]'), "仿真花")
        Forever = kindChange1(request.POST.get('like[Forever]'), "永生花")
        Dry = kindChange1(request.POST.get('like[Dry]'), "干花")
        Green = kindChange1(request.POST.get('like[Green]'), "绿植")
        Vase = kindChange1(request.POST.get('like[Vase]'), "花瓶")

        # 2.处理种类数据
        kinds = [Fresh, Fake, Forever, Dry, Green, Vase]
        print(kinds)
        kinds = list(set(kinds))
        for i in kinds:
            if i == 'None':
                kinds.remove(i)
        allKinds = ""
        for i in kinds:
            allKinds += i + "|"
        allKinds = allKinds[:-1]
        if len(allKinds) == 0:
            allKinds = "无"

        # 3.将数据进行保存
        business = Bussiness.objects.get(id=token)
        business.name = businessName
        business.email = businessEmail
        business.addr = businessAddr
        business.emailRemind = businessRemind
        business.signature = businessSignature
        business.kinds = allKinds
        business.save()

        contex = {
            'business': business,
            'kinds': kinds,
        }
        return render(request, 'bus_center_info_dian.html', contex)


class BusCenterInfoPersonView(View):
    """用户中心"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, token):
        """商家中心-联系人页面"""
        business = Bussiness.objects.get(id=token)
        contex = {
            'business': business,
        }
        return render(request, 'bus_center_info_person.html', contex)


class BusCenterInfoPersonChangeView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, token):
        """联系人信息"""
        business = Bussiness.objects.get(id=token)
        contex = {
            'business': business,
        }
        return render(request, 'bus_center_info_person_change.html', contex)

    def post(self, request, token):
        """店铺信息修改"""
        # 1.获取请求中传递过来的信息
        personName = request.POST.get('personName')
        personSex = sexChange(request.POST.get('sex'))
        personAge = request.POST.get('personAge')
        personEmail = request.POST.get('personEmail')
        personDate = request.POST.get('personDate')
        personAddr = request.POST.get('interest')
        personRemind = emailChange(request.POST.get('personRemind'))
        personDescription = request.POST.get('personDescription')

        # 2.将数据进行保存
        business = Bussiness.objects.get(id=token)
        business.personName = personName
        business.personSex = personSex
        business.personAge = personAge
        business.personEmail = personEmail
        business.personDate = personDate
        business.personAddr = personAddr
        business.personEmailRemind = personRemind
        business.personDescription = personDescription
        business.save()

        contex = {
            'business': business,
        }
        return render(request, 'bus_center_info_person.html', contex)


class BusCenterGoodsSearchView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, token):
        """商品信息"""
        business = Bussiness.objects.get(id=token)
        contex = {
            'business': business,
        }
        return render(request, 'bus_center_goods_search.html', contex)


class BusCenterTypesSearchView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, token):
        """种类信息"""
        business = Bussiness.objects.get(id=token)
        contex = {
            'business': business,
        }
        return render(request, 'bus_center_types_search.html', contex)


class BusCenterGoodsSearch0View(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, token):
        """商品信息"""
        business = Bussiness.objects.get(id=token)
        contex = {
            'business': business,
        }
        return render(request, 'bus_center_goods_search0.html', contex)


class BusCenterGoodsSearch1View(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, token):
        """商品信息"""
        business = Bussiness.objects.get(id=token)
        contex = {
            'business': business,
        }
        return render(request, 'bus_center_goods_search1.html', contex)


class BusCenterGoodsSearch2View(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, token):
        """商品信息"""
        business = Bussiness.objects.get(id=token)
        contex = {
            'business': business,
        }
        return render(request, 'bus_center_goods_search2.html', contex)


class BusCenterOrderSearch1View(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, token, page):
        """商品信息"""
        # 获得商家信息
        business = Bussiness.objects.get(id=token)

        # 获得商家已有的全部订单编号
        orderSons = OrderSons.objects.filter(bussiness=business)

        # 找出每个订单内属于该商家的物品
        for ordersons in orderSons:
            orderInfo = OrderInfo.objects.get(order_id=ordersons.order_id)

            # 获取该订单中属于该商家所出售的商品
            orderGoods = OrderGoods.objects.filter(order_id=orderInfo.order_id, business=business.id)
            for order_sku in orderGoods:
                amount = order_sku.count * order_sku.price
                order_sku.amount = amount

            ordersons.orderInfo = orderInfo
            ordersons.orderGoods = orderGoods
            ordersons.status_name = OrderInfo.ORDER_STATUS[ordersons.orderInfo.order_status]
            ordersons.transit_price = OrderInfo.transit_price

            print(ordersons.transit_price)
        paginator = Paginator(orderSons, 5)

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
            'business': business,
            'orderSons': orderSons,
        }
        return render(request, 'bus_center_order_search1.html', contex)


class BusCenterOrderSearch2View(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, token, page):
        """商品信息"""
        # 获得商家信息
        business = Bussiness.objects.get(id=token)

        # 获得商家已有的全部订单编号
        orderSons = OrderSons.objects.filter(bussiness=business, order__order_status=1)
        print(orderSons)

        # 找出每个订单内属于该商家的物品
        for ordersons in orderSons:
            orderInfo = OrderInfo.objects.get(order_id=ordersons.order_id)

            # 获取该订单中属于该商家所出售的商品
            orderGoods = OrderGoods.objects.filter(order_id=orderInfo.order_id, business=business.id)
            for order_sku in orderGoods:
                amount = order_sku.count * order_sku.price
                order_sku.amount = amount

            ordersons.orderInfo = orderInfo
            ordersons.orderGoods = orderGoods
            ordersons.status_name = OrderInfo.ORDER_STATUS[ordersons.orderInfo.order_status]
            ordersons.transit_price = OrderInfo.transit_price

            print(ordersons.transit_price)
        paginator = Paginator(orderSons, 5)

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
            'business': business,
            'orderSons': orderSons,
        }
        return render(request, 'bus_center_order_search2.html', contex)


class BusCenterOrderSearch3View(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, token, page):
        """商品信息"""
        # 获得商家信息
        business = Bussiness.objects.get(id=token)

        # 获得商家已有的全部订单编号
        orderSons = OrderSons.objects.filter(bussiness=business, order__order_status__in=[2, 3])
        print(orderSons)

        # 找出每个订单内属于该商家的物品
        for ordersons in orderSons:
            orderInfo = OrderInfo.objects.get(order_id=ordersons.order_id)

            # 获取该订单中属于该商家所出售的商品
            orderGoods = OrderGoods.objects.filter(order_id=orderInfo.order_id, business=business.id)
            for order_sku in orderGoods:
                amount = order_sku.count * order_sku.price
                order_sku.amount = amount

            ordersons.orderInfo = orderInfo
            ordersons.orderGoods = orderGoods
            ordersons.status_name = OrderInfo.ORDER_STATUS[ordersons.orderInfo.order_status]
            ordersons.transit_price = OrderInfo.transit_price

            print(ordersons.transit_price)
        paginator = Paginator(orderSons, 5)

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
            'business': business,
            'orderSons': orderSons,
        }
        return render(request, 'bus_center_order_search3.html', contex)


class BusCenterOrderSearch4View(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, token, page):
        """商品信息"""
        # 获得商家信息
        business = Bussiness.objects.get(id=token)

        # 获得商家已有的全部订单编号
        orderSons = OrderSons.objects.filter(bussiness=business, order__order_status=4)
        print(orderSons)

        # 找出每个订单内属于该商家的物品
        for ordersons in orderSons:
            orderInfo = OrderInfo.objects.get(order_id=ordersons.order_id)

            # 获取该订单中属于该商家所出售的商品
            orderGoods = OrderGoods.objects.filter(order_id=orderInfo.order_id, business=business.id)
            for order_sku in orderGoods:
                amount = order_sku.count * order_sku.price
                order_sku.amount = amount

            ordersons.orderInfo = orderInfo
            ordersons.orderGoods = orderGoods
            ordersons.status_name = OrderInfo.ORDER_STATUS[ordersons.orderInfo.order_status]
            ordersons.transit_price = OrderInfo.transit_price

            print(ordersons.transit_price)
        paginator = Paginator(orderSons, 5)

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
            'business': business,
            'orderSons': orderSons,
        }
        return render(request, 'bus_center_order_search4.html', contex)


class BusCenterOrderSearch5View(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, token, page):
        """商品信息"""
        # 获得商家信息
        business = Bussiness.objects.get(id=token)

        # 获得商家已有的全部订单编号
        orderSons = OrderSons.objects.filter(bussiness=business, order__order_status=5)
        print(orderSons)

        # 找出每个订单内属于该商家的物品
        for ordersons in orderSons:
            orderInfo = OrderInfo.objects.get(order_id=ordersons.order_id)

            # 获取该订单中属于该商家所出售的商品
            orderGoods = OrderGoods.objects.filter(order_id=orderInfo.order_id, business=business.id)
            for order_sku in orderGoods:
                amount = order_sku.count * order_sku.price
                order_sku.amount = amount

            ordersons.orderInfo = orderInfo
            ordersons.orderGoods = orderGoods
            ordersons.status_name = OrderInfo.ORDER_STATUS[ordersons.orderInfo.order_status]
            ordersons.transit_price = OrderInfo.transit_price

            print(ordersons.transit_price)
        paginator = Paginator(orderSons, 5)

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
            'business': business,
            'orderSons': orderSons,
        }
        return render(request, 'bus_center_order_search5.html', contex)


class BusCenterDeleteGoodsView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request):
        try:
            ID = request.GET.get('id')
            GoodsSKU.objects.get(id=ID).delete()
            # resultdict = {}
            # resultdict['status'] = 200
            return HttpResponse(200)
        except:
            return HttpResponse(0)


class BusCenterDeleteTypesView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request):
        try:
            ID = request.GET.get('id')
            Goods.objects.get(id=ID).delete()
            # resultdict = {}
            # resultdict['status'] = 200
            return HttpResponse(200)
        except:
            return HttpResponse(0)


class BusCenterEditGoodsView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def post(self, request):
        try:
            id = request.POST.get('id')
            name = request.POST.get('name')
            desc = request.POST.get('desc')
            price = request.POST.get('price')
            stock = request.POST.get('stock')
            unite = request.POST.get('unite')
            status = request.POST.get('status')
            type = request.POST.get('type')
            image = request.POST.get('image123456')
            goodssku = GoodsSKU.objects.get(id=id)
            goodssku.name = name
            goodssku.desc = desc
            goodssku.price = price
            goodssku.stock = stock
            goodssku.unite = unite
            goodssku.status = status
            goodssku.type_id = type
            if image != "None":
                goodssku.image = image
            goodssku.save()
            # resultdict = {}
            # resultdict['status'] = 200
            dict = {}
            dict['src'] = "None"
            data = {"code": 200, "msg": "1", "data": dict}
            print(data)
            return JsonResponse(data)
        except:
            dict = {}
            dict['src'] = "None"
            data = {"code": 0, "msg": "1", "data": dict}
            return JsonResponse(data)


class BusCenterEditTypesView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def post(self, request):
        try:
            id = request.POST.get('id')
            name = request.POST.get('name')
            detail = request.POST.get('detail')
            print(name)
            print(detail)
            goods = Goods.objects.get(id=id)
            goods.name = name
            goods.detail = detail
            goods.save()
            # resultdict = {}
            # resultdict['status'] = 200
            dict = {}
            dict['src'] = "None"
            data = {"code": 200, "msg": "1", "data": dict}
            print(data)
            return JsonResponse(data)
        except:
            dict = {}
            dict['src'] = "None"
            data = {"code": 0, "msg": "1", "data": dict}
            return JsonResponse(data)


class BusCenterUploadImageView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def post(self, request):
        try:
            file = request.FILES.get('file')
            # 将文件上传至FastDFS文件系统
            # 创建一个Fdfs_client 对象
            client_conf = get_tracker_conf(settings.FDFS_CLIENT_CONF)
            client = Fdfs_client(client_conf)
            # 上传文件到系统中
            res = client.upload_by_buffer(file.file.read())
            filename = res.get('Remote file_id')
            filename = filename.decode()
            print(filename)
            dict = {}
            dict['src'] = filename
            data = {"code": 0, "msg": "1", "data": dict}
            print(data)
            return JsonResponse(data)
        except:
            dict = {}
            dict['src'] = "None"
            data = {"code": 200, "msg": "1", "data": dict}
            return JsonResponse(data)


def SelectGoodsSKU(request, token):
    name = request.GET.get('name')
    flag = request.GET.get('flag')
    if (flag):
        if len(str(name)) > 0:
            goodssku = GoodsSKU.objects.filter(name=name, business=token)
            total = goodssku.count()
            resultdict = {}
            resultdict['total'] = total
            dict = []
            for p in goodssku:
                dic = {}
                dic['id'] = p.id
                dic['image'] = p.image.url
                dic['name'] = p.name
                dic['desc'] = p.desc
                dic['price'] = p.price
                dic['unite'] = p.unite
                dic['sale'] = p.sales
                dic['stock'] = p.stock
                dic['status'] = GoodsSKU.status_choices[p.status]
                dict.append(dic)
            resultdict['code'] = 0
            resultdict['msg'] = "1"
            resultdict['count'] = total
            resultdict['data'] = dict
        else:
            goodssku = GoodsSKU.objects.filter(business=token)
            total = goodssku.count()
            resultdict = {}
            resultdict['total'] = total
            dict = []
            for p in goodssku:
                dic = {}
                dic['id'] = p.id
                dic['image'] = p.image.url
                dic['name'] = p.name
                dic['desc'] = p.desc
                dic['price'] = p.price
                dic['unite'] = p.unite
                dic['sale'] = p.sales
                dic['stock'] = p.stock
                dic['status'] = GoodsSKU.status_choices[p.status]
                dict.append(dic)
            resultdict['code'] = 0
            resultdict['msg'] = "1"
            resultdict['count'] = total
            resultdict['data'] = dict
    else:
        goodssku = GoodsSKU.objects.filter(business=token)
        total = goodssku.count()
        resultdict = {}
        resultdict['total'] = total
        dict = []
        for p in goodssku:
            dic = {}
            dic['id'] = p.id
            dic['image'] = p.image.url
            dic['name'] = p.name
            dic['desc'] = p.desc
            dic['price'] = p.price
            dic['unite'] = p.unite
            dic['sale'] = p.sales
            dic['stock'] = p.stock
            dic['status'] = GoodsSKU.status_choices[p.status]
            dict.append(dic)
        resultdict['code'] = 0
        resultdict['msg'] = "1"
        resultdict['count'] = total
        resultdict['data'] = dict
    return JsonResponse(resultdict)


def SelectGoodsSKU0(request, token):
    name = request.GET.get('name')
    flag = request.GET.get('flag')
    if (flag):
        if len(str(name)) > 0:
            goodssku = GoodsSKU.objects.filter(name=name, status=0, business=token)
            total = goodssku.count()
            resultdict = {}
            resultdict['total'] = total
            dict = []
            for p in goodssku:
                dic = {}
                dic['id'] = p.id
                dic['image'] = p.image.url
                dic['name'] = p.name
                dic['desc'] = p.desc
                dic['price'] = p.price
                dic['unite'] = p.unite
                dic['sale'] = p.sales
                dic['stock'] = p.stock
                dic['status'] = GoodsSKU.status_choices[p.status]
                dict.append(dic)
            resultdict['code'] = 0
            resultdict['msg'] = "1"
            resultdict['count'] = total
            resultdict['data'] = dict
        else:
            goodssku = GoodsSKU.objects.filter(status=0, business=token)
            total = goodssku.count()
            resultdict = {}
            resultdict['total'] = total
            dict = []
            for p in goodssku:
                dic = {}
                dic['id'] = p.id
                dic['image'] = p.image.url
                dic['name'] = p.name
                dic['desc'] = p.desc
                dic['price'] = p.price
                dic['unite'] = p.unite
                dic['sale'] = p.sales
                dic['stock'] = p.stock
                dic['status'] = GoodsSKU.status_choices[p.status]
                dict.append(dic)
            resultdict['code'] = 0
            resultdict['msg'] = "1"
            resultdict['count'] = total
            resultdict['data'] = dict
    else:
        goodssku = GoodsSKU.objects.filter(status=0, business=token)
        total = goodssku.count()
        resultdict = {}
        resultdict['total'] = total
        dict = []
        for p in goodssku:
            dic = {}
            dic['id'] = p.id
            dic['image'] = p.image.url
            dic['name'] = p.name
            dic['desc'] = p.desc
            dic['price'] = p.price
            dic['unite'] = p.unite
            dic['sale'] = p.sales
            dic['stock'] = p.stock
            dic['status'] = GoodsSKU.status_choices[p.status]
            dict.append(dic)
        resultdict['code'] = 0
        resultdict['msg'] = "1"
        resultdict['count'] = total
        resultdict['data'] = dict
    return JsonResponse(resultdict)


def SelectGoodsSKU1(request, token):
    name = request.GET.get('name')
    flag = request.GET.get('flag')
    if (flag):
        if len(str(name)) > 0:
            goodssku = GoodsSKU.objects.filter(name=name, status=1, business=token)
            total = goodssku.count()
            resultdict = {}
            resultdict['total'] = total
            dict = []
            for p in goodssku:
                dic = {}
                dic['id'] = p.id
                dic['image'] = p.image.url
                dic['name'] = p.name
                dic['desc'] = p.desc
                dic['price'] = p.price
                dic['unite'] = p.unite
                dic['sale'] = p.sales
                dic['stock'] = p.stock
                dic['status'] = GoodsSKU.status_choices[p.status]
                dict.append(dic)
            resultdict['code'] = 0
            resultdict['msg'] = "1"
            resultdict['count'] = total
            resultdict['data'] = dict
        else:
            goodssku = GoodsSKU.objects.filter(status=1, business=token)
            total = goodssku.count()
            resultdict = {}
            resultdict['total'] = total
            dict = []
            for p in goodssku:
                dic = {}
                dic['id'] = p.id
                dic['image'] = p.image.url
                dic['name'] = p.name
                dic['desc'] = p.desc
                dic['price'] = p.price
                dic['unite'] = p.unite
                dic['sale'] = p.sales
                dic['stock'] = p.stock
                dic['status'] = GoodsSKU.status_choices[p.status]
                dict.append(dic)
            resultdict['code'] = 0
            resultdict['msg'] = "1"
            resultdict['count'] = total
            resultdict['data'] = dict
    else:
        goodssku = GoodsSKU.objects.filter(status=1, business=token)
        total = goodssku.count()
        resultdict = {}
        resultdict['total'] = total
        dict = []
        for p in goodssku:
            dic = {}
            dic['id'] = p.id
            dic['image'] = p.image.url
            dic['name'] = p.name
            dic['desc'] = p.desc
            dic['price'] = p.price
            dic['unite'] = p.unite
            dic['sale'] = p.sales
            dic['stock'] = p.stock
            dic['status'] = GoodsSKU.status_choices[p.status]
            dict.append(dic)
        resultdict['code'] = 0
        resultdict['msg'] = "1"
        resultdict['count'] = total
        resultdict['data'] = dict
    return JsonResponse(resultdict)


def SelectGoodsSKU2(request, token):
    name = request.GET.get('name')
    flag = request.GET.get('flag')
    if (flag):
        if len(str(name)) > 0:
            goodssku = GoodsSKU.objects.filter(name=name, status=2, business=token)
            total = goodssku.count()
            resultdict = {}
            resultdict['total'] = total
            dict = []
            for p in goodssku:
                dic = {}
                dic['id'] = p.id
                dic['image'] = p.image.url
                dic['name'] = p.name
                dic['desc'] = p.desc
                dic['price'] = p.price
                dic['unite'] = p.unite
                dic['sale'] = p.sales
                dic['stock'] = p.stock
                dic['status'] = GoodsSKU.status_choices[p.status]
                dict.append(dic)
            resultdict['code'] = 0
            resultdict['msg'] = "1"
            resultdict['count'] = total
            resultdict['data'] = dict
        else:
            goodssku = GoodsSKU.objects.filter(status=2, business=token)
            total = goodssku.count()
            resultdict = {}
            resultdict['total'] = total
            dict = []
            for p in goodssku:
                dic = {}
                dic['id'] = p.id
                dic['image'] = p.image.url
                dic['name'] = p.name
                dic['desc'] = p.desc
                dic['price'] = p.price
                dic['unite'] = p.unite
                dic['sale'] = p.sales
                dic['stock'] = p.stock
                dic['status'] = GoodsSKU.status_choices[p.status]
                dict.append(dic)
            resultdict['code'] = 0
            resultdict['msg'] = "1"
            resultdict['count'] = total
            resultdict['data'] = dict
    else:
        goodssku = GoodsSKU.objects.filter(status=2, business=token)
        total = goodssku.count()
        resultdict = {}
        resultdict['total'] = total
        dict = []
        for p in goodssku:
            dic = {}
            dic['id'] = p.id
            dic['image'] = p.image.url
            dic['name'] = p.name
            dic['desc'] = p.desc
            dic['price'] = p.price
            dic['unite'] = p.unite
            dic['sale'] = p.sales
            dic['stock'] = p.stock
            dic['status'] = GoodsSKU.status_choices[p.status]
            dict.append(dic)
        resultdict['code'] = 0
        resultdict['msg'] = "1"
        resultdict['count'] = total
        resultdict['data'] = dict
    return JsonResponse(resultdict)


def SelectTypesSKU(request, token):
    name = request.GET.get('name')
    flag = request.GET.get('flag')
    if (flag):
        if len(str(name)) > 0:
            goods = Goods.objects.filter(name=name, business=token)
            total = goods.count()
            resultdict = {}
            resultdict['total'] = total
            dict = []
            for p in goods:
                dic = {}
                dic['id'] = p.id
                dic['name'] = p.name
                dic['detail'] = p.detail
                dic['create_time'] = p.create_time
                dic['update_time'] = p.update_time
                dict.append(dic)
            resultdict['code'] = 0
            resultdict['msg'] = "1"
            resultdict['count'] = total
            resultdict['data'] = dict
        else:
            goods = Goods.objects.filter(business=token)
            total = goods.count()
            resultdict = {}
            resultdict['total'] = total
            dict = []
            for p in goods:
                dic = {}
                dic['id'] = p.id
                dic['name'] = p.name
                dic['detail'] = p.detail
                dic['create_time'] = p.create_time
                dic['update_time'] = p.update_time
                dict.append(dic)
            resultdict['code'] = 0
            resultdict['msg'] = "1"
            resultdict['count'] = total
            resultdict['data'] = dict
    else:
        goods = Goods.objects.filter(business=token)
        total = goods.count()
        resultdict = {}
        resultdict['total'] = total
        dict = []
        for p in goods:
            dic = {}
            dic['id'] = p.id
            dic['name'] = p.name
            dic['detail'] = p.detail
            dic['create_time'] = p.create_time
            dic['update_time'] = p.update_time
            dict.append(dic)
        resultdict['code'] = 0
        resultdict['msg'] = "1"
        resultdict['count'] = total
        resultdict['data'] = dict
    print(resultdict)
    return JsonResponse(resultdict)


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
            business_id = info['confirm']

            # 根据id获取用户信息
            business = Bussiness.objects.get(id=business_id)
            business.is_active = 1
            business.save()

            # 返回应答，跳转至登录页面

            return redirect(reverse('bussiness:login'))
        except SignatureExpired as e:
            return HttpResponse('激活链接已过期')


class BusCenterAddTypesView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def post(self, request):
        try:
            id = request.POST.get('id')
            name = request.POST.get('name')
            detail = request.POST.get('detail')
            goods = Goods.objects.create(business=id, name=name, detail=detail)
            goods.save()
            # resultdict = {}
            # resultdict['status'] = 200
            dict = {}
            dict['src'] = "None"
            data = {"code": 200, "msg": "1", "data": dict}
            print(data)
            return JsonResponse(data)
        except:
            dict = {}
            dict['src'] = "None"
            data = {"code": 0, "msg": "1", "data": dict}
            return JsonResponse(data)


class BusCenterAddGoodsView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def post(self, request):
        try:
            id = request.POST.get('id')
            name = request.POST.get('name')
            desc = request.POST.get('desc')
            price = request.POST.get('price')
            unite = request.POST.get('unite')
            stock = request.POST.get('stock')
            type = request.POST.get('type')
            status = request.POST.get('status')
            avator = request.POST.get('avator')
            image123456 = request.POST.get('image123456')
            goodstype = request.POST.get('goodstype')

            print('id', id)
            print('name', name)
            print('desc', desc)
            print('price', price)
            print('unite', unite)
            print('stock', stock)
            print('type', type)
            print('status', status)
            print('avator', avator)
            print('mage123456', image123456)
            print('goodstype', goodstype)

            # 创建商品
            goods_sku = GoodsSKU.objects.create(name=name, desc=desc, price=price, unite=unite,
                                                image=image123456, stock=stock, sales=0,
                                                status=status, goods_id=goodstype, type_id=type,
                                                business=id)
            goods_sku.save()
            dict = {}
            dict['src'] = "None"
            data = {"code": 200, "msg": "1", "data": dict}
            print(data)
            return JsonResponse(data)
        except:
            dict = {}
            dict['src'] = "None"
            data = {"code": 0, "msg": "1", "data": dict}
            return JsonResponse(data)


class BusCenterUpdateDianImageView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def post(self, request):
        try:
            id = request.POST.get('id')
            image123456 = request.POST.get('image123456')
            print(image123456)

            business = Bussiness.objects.get(id=id)
            business.image = image123456
            business.save()

            # 创建商品
            dict = {}
            dict['src'] = "None"
            data = {"code": 200, "msg": "1", "data": dict}
            print(data)
            return JsonResponse(data)
        except:
            dict = {}
            dict['src'] = "None"
            data = {"code": 0, "msg": "1", "data": dict}
            return JsonResponse(data)


class BusCenterUpdatePersonImageView(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def post(self, request):
        try:
            id = request.POST.get('id')
            image123456 = request.POST.get('image123456')
            print('image123456', image123456)

            business = Bussiness.objects.get(id=id)
            business.personImage = image123456
            business.save()
            # 创建商品
            dict = {}
            dict['src'] = "None"
            data = {"code": 200, "msg": "1", "data": dict}
            print(data)
            return JsonResponse(data)
        except:
            dict = {}
            dict['src'] = "None"
            data = {"code": 0, "msg": "1", "data": dict}
            return JsonResponse(data)


class BusCenterDataSearch0View(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, token):
        # 获得商家信息
        business = Bussiness.objects.get(id=token)

        # 获得该商家的订单信息
        # 获得商家已有的全部订单编号
        orderToPay=0 # 用户待付款的订单
        orderProcessing=0 # 用户已付款正在走物流的订单
        orderDone=0 # 已经完成的订单（包含已评价或者未评价）
        orderMoney=0 #
        orderSons = OrderSons.objects.filter(bussiness=business)

        # 找出每个订单的信息
        for ordersons in orderSons:
            orderInfo = OrderInfo.objects.get(order_id=ordersons.order_id)
            if(orderInfo.order_status==1):
                orderToPay+=1
            elif(orderInfo.order_status in [2,3]):
                orderProcessing+=1
            else:
                orderDone+=1
                orderMoney+=orderInfo.total_price
        orderCount = orderToPay+orderProcessing+orderDone

        # 获取商品数
        FreshGoods = GoodsSKU.objects.filter(business=business.id,type_id=1).count()
        FakeGoods = GoodsSKU.objects.filter(business=business.id,type_id=2).count()
        ForeverGoods = GoodsSKU.objects.filter(business=business.id,type_id=3).count()
        GreenGoods = GoodsSKU.objects.filter(business=business.id,type_id=4).count()
        DryGoods = GoodsSKU.objects.filter(business=business.id,type_id=5).count()
        VaseGoods = GoodsSKU.objects.filter(business=business.id,type_id=6).count()
        GoodsAll = FreshGoods+FakeGoods+ForeverGoods+GreenGoods+DryGoods+VaseGoods

        # 获取类别数
        FreshType = []
        FakeType = []
        ForeverType = []
        GreenType = []
        DryType = []
        VaseType = []
        Good = GoodsSKU.objects.filter(business=business.id)
        for good in Good:
            if good.type_id == 1:
                FreshType.append(good.goods_id)
            elif good.type_id == 2:
                FakeType.append(good.goods_id)
            elif good.type_id == 3:
                ForeverType.append(good.goods_id)
            elif good.type_id == 4:
                GreenType.append(good.goods_id)
            elif good.type_id == 5:
                DryType.append(good.goods_id)
            elif good.type_id == 6:
                VaseType.append(good.goods_id)
        FreshType = len(list(set(FreshType)))
        FakeType = len(list(set(FakeType)))
        ForeverType = len(list(set(ForeverType)))
        GreenType = len(list(set(GreenType)))
        DryType = len(list(set(DryType)))
        VaseType = len(list(set(VaseType)))
        TypeAll = FreshType+FakeType+ForeverType+GreenType+DryType+VaseType

        contex = {
            'orderTopay': orderToPay,
            'orderProcessing':orderProcessing,
            'orderDone':orderDone,
            'orderMoney':orderMoney,
            'orderCount': orderCount,
            'business': business,
            'FreshGoods': FreshGoods,
            'FakeGoods': FakeGoods,
            'ForeverGoods': ForeverGoods,
            'GreenGoods': GreenGoods,
            'DryGoods': DryGoods,
            'VaseGoods': VaseGoods,
            'GoodsAll': GoodsAll,
            'FreshType': FreshType,
            'FakeType': FakeType,
            'ForeverType': ForeverType,
            'GreenType': GreenType,
            'DryType': DryType,
            'VaseType': VaseType,
            'TypeAll': TypeAll,
        }
        return render(request, 'bus_center_datasearch0.html', contex)


    def post(self, request):
        pass


class BusCenterDataSearch1View(View):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def get(self, request, token):
        # 获得商家信息
        business = Bussiness.objects.get(id=token)
        contex = {
            'business': business,
        }
        return render(request, 'bus_center_datasearch1.html', contex)


    def post(self, request):
        pass


def DataSearchSingle(request, token):
    name = request.GET.get('name')
    flag = request.GET.get('flag')
    if (flag):
        if len(str(name)) > 0:
            goodssku = GoodsSKU.objects.filter(name=name,business=token)
            total = goodssku.count()
            resultdict = {}
            resultdict['total'] = total
            dict = []
            for p in goodssku:
                dic = {}
                dic['id'] = p.id
                dic['image'] = p.image.url
                dic['name'] = p.name
                dic['price'] = p.price
                dic['unite'] = p.unite
                dic['sale'] = p.sales
                dic['stock'] = p.stock
                dic['kind'] = p.type.name
                dic['type'] = p.goods.name
                dic['status'] = GoodsSKU.status_choices[p.status]
                dict.append(dic)
            resultdict['code'] = 0
            resultdict['msg'] = "1"
            resultdict['count'] = total
            resultdict['data'] = dict
        else:
            goodssku = GoodsSKU.objects.filter(business=token)
            total = goodssku.count()
            resultdict = {}
            resultdict['total'] = total
            dict = []
            for p in goodssku:
                dic = {}
                dic['id'] = p.id
                dic['image'] = p.image.url
                dic['name'] = p.name
                dic['price'] = p.price
                dic['unite'] = p.unite
                dic['sale'] = p.sales
                dic['stock'] = p.stock
                dic['kind'] = p.type.name
                dic['type'] = p.goods.name
                dic['status'] = GoodsSKU.status_choices[p.status]
                dict.append(dic)
            resultdict['code'] = 0
            resultdict['msg'] = "1"
            resultdict['count'] = total
            resultdict['data'] = dict
    else:
        goodssku = GoodsSKU.objects.filter(business=token)
        total = goodssku.count()
        resultdict = {}
        resultdict['total'] = total
        dict = []
        for p in goodssku:
            dic = {}
            dic['id'] = p.id
            dic['image'] = p.image.url
            dic['name'] = p.name
            dic['price'] = p.price
            dic['unite'] = p.unite
            dic['sale'] = p.sales
            dic['stock'] = p.stock
            dic['kind'] = p.type.name
            dic['type'] = p.goods.name
            dic['status'] = GoodsSKU.status_choices[p.status]
            dict.append(dic)
        resultdict['code'] = 0
        resultdict['msg'] = "1"
        resultdict['count'] = total
        resultdict['data'] = dict
    return JsonResponse(resultdict)