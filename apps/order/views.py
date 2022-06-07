from django.shortcuts import render, redirect, reverse
from django.views.generic import View

from apps.bussiness.models import Bussiness
from apps.goods.models import GoodsSKU
from apps.user.models import Address
from apps.order.models import OrderInfo, OrderGoods, OrderSons
from django.http import JsonResponse
from django.db import transaction
from django.conf import settings
from django.views.generic import View
from django_redis import get_redis_connection
from utils.mixin import LoginRequiredMixin
from datetime import datetime
from django.db import transaction
from alipay import AliPay
from django.conf import settings
import os
import os


# Create your views here.
# order/place
class OrderPlaceView(View):
    def post(self, request):
        """提交订单显示"""
        sku_ids = request.POST.getlist('sku_ids')
        user = request.user

        # 校验参数
        if not sku_ids:
            # 跳转到购物车页面
            return redirect(reverse('cart:show'))
        # 从redis拿到数据
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        # 遍历sku_ids，获取用户要购买的商品的信息
        skus = []
        total_count = 0
        total_price = 0
        for sku_id in sku_ids:
            # 根据商品的id获取商品的信息
            sku = GoodsSKU.objects.get(id=sku_id)
            count = conn.hget(cart_key, sku_id)
            # 计算商品小计
            amount = sku.price * int(count)
            # 动态增加属性 count保存购买商品数量，amount保存商品小计
            sku.count = count.decode()
            sku.amount = amount
            skus.append(sku)

            total_count += int(count)
            total_price += amount

        # 运费实际开发的时候有一个子系统
        transit_price = 10
        # 实付款
        total_pay = total_price + transit_price

        # 获取用户的收件地址
        addrs = Address.objects.filter(user=user)
        # 组织上下文
        sku_ids = ','.join(sku_ids)
        contex = {
            'skus': skus,
            'total_count': total_count,
            'total_price': total_price,
            'transit_price': transit_price,
            'total_pay': total_pay,
            'addrs': addrs,
            'sku_ids': sku_ids,
        }

        return render(request, 'place_order.html', contex)


# 前端传递的参数: 地址id(addr_id) 支付方式(pay_method) 用户要购买的商品id字符串(sku_ids)
# mysql事务: 要么都成功，要么都失败
# 高并发：秒杀
# 支付宝支付(悲观锁版)
class OrderCommitView1(LoginRequiredMixin, View):
    """订单创建"""

    @transaction.atomic
    def post(self, request):
        """订单创建"""
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})
        # 接收参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')  # 1,3

        # 校验参数
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})

        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 2, 'errmsg': '非法的支付方式'})

        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            # 地址不存在
            return JsonResponse({'res': 3, 'errmsg': '地址非法'})

        # todo: 创建订单核心业务

        # 组织参数
        # 订单id: 20171122181630+用户id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)

        # 运费
        transit_price = 10

        # 总数目和总金额
        total_count = 0
        total_price = 0

        # 设置事务保存点
        save_id = transaction.savepoint()

        try:
            # todo: 向df_order_info表中添加一条记录
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price)

            # todo: 用户的订单中有几个商品，需要向df_order_goods表中加入几条记录
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id

            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                # 获取商品的信息
                try:
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                except:
                    # 商品不存在
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 4, 'errmsg': '商品不存在'})

                # 从redis中获取用户所要购买的商品的数量
                count = conn.hget(cart_key, sku_id)

                # todo: 判断商品的库存
                if int(count) > sku.stock:
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                # todo: 向df_order_goods表中添加一条记录
                OrderGoods.objects.create(order=order,
                                          sku=sku,
                                          count=count,
                                          price=sku.price)

                # todo: 更新商品的库存和销量
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()

                # todo: 累加计算订单商品的总数量和总价格
                amount = sku.price * int(count)
                total_count += int(count)
                total_price += amount

            # todo: 更新订单信息表中的商品的总数量和总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()


        except:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})

        # 提交事务
        transaction.savepoint_commit(save_id)
        # todo: 清除用户购物车中对应的记录
        conn.hdel(cart_key, *sku_ids)
        # 返回应答
        return JsonResponse({'res': 5, 'message': '创建成功'})


# 前端传递的参数: 地址id(addr_id) 支付方式(pay_method) 用户要购买的商品id字符串(sku_ids)
# mysql事务: 要么都成功，要么都失败
# 高并发：秒杀
# 支付宝支付(乐观锁版,查询不加锁，设置数据时判断)
class OrderCommitView(LoginRequiredMixin, View):
    """订单创建"""

    @transaction.atomic
    def post(self, request):
        """订单创建"""
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})
        # 接收参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')  # 1,3

        # 校验参数
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})

        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 2, 'errmsg': '非法的支付方式'})

        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            # 地址不存在
            return JsonResponse({'res': 3, 'errmsg': '地址非法'})

        # todo: 创建订单核心业务

        # 组织参数

        # 运费
        transit_price = 10

        # 设置事务保存点
        save_id = transaction.savepoint()
        try:
            # 检查当前购物车的所有商品中存在几个商家的商品
            Business = []
            sku_ids1 = sku_ids.split(',')
            for sku_id in sku_ids1:
                sku = GoodsSKU.objects.get(id=sku_id)
                Business.append(sku.business)
            Business = set(Business)
            Business = list(Business)  # 至此获取订单中包含的商家个数
            sku_ids = sku_ids.split(',')
            for business in Business:
                # todo: 向df_order_info表中添加一条记录
                # 订单id: 20171122181630+用户id+商家id
                order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id) + str(business)
                # 总数目和总金额
                total_count = 0
                total_price = 0
                order = OrderInfo.objects.create(order_id=order_id,
                                                 user=user,
                                                 addr=addr,
                                                 pay_method=pay_method,
                                                 total_count=total_count,
                                                 total_price=total_price,
                                                 transit_price=transit_price)

                # todo: 用户的订单中有几个商品，需要向df_order_goods表中加入几条记录
                conn = get_redis_connection('default')
                cart_key = 'cart_%d' % user.id

                for sku_id in sku_ids:
                    sku1 = GoodsSKU.objects.get(id=sku_id)
                    if sku1.business != business:
                        continue
                    # 获取商品的信息
                    for i in range(3):  # 信息延误，尽可能多次尝试
                        try:
                            # 选择从place_order传递过来的商品列表中属于该商品的一类
                            sku = GoodsSKU.objects.get(id=sku_id)
                        except:
                            # 商品不存在
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res': 4, 'errmsg': '商品不存在'})
                        # 从redis中获取用户所要购买的商品的数量
                        count = conn.hget(cart_key, sku_id)

                        # todo: 判断商品的库存
                        if int(count) > sku.stock:
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                        # todo: 更新商品的库存和销量
                        # sku.stock -= int(count)
                        # sku.sales += int(count)
                        # sku.save()
                        orgin_stock = sku.stock
                        new_stock = orgin_stock - int(count)
                        new_sales = sku.sales + int(count)

                        # 返回受影响的行数
                        res = GoodsSKU.objects.filter(id=sku_id, stock=orgin_stock).update(stock=new_stock,
                                                                                           sales=new_sales)

                        if res == 0:
                            if i == 2:
                                transaction.savepoint_rollback(save_id)
                                return JsonResponse({'res': 7, 'errmsg': '下单失败2'})
                            continue

                        # todo: 向df_order_goods表中添加一条记录
                        OrderGoods.objects.create(order=order,
                                                  sku=sku,
                                                  count=count,
                                                  price=sku.price,
                                                  business=business)

                        # todo: 累加计算订单商品的总数量和总价格
                        amount = sku.price * int(count)
                        total_count += int(count)
                        total_price += amount

                        # 跳出了循环
                        break

                # todo: 更新订单信息表中的商品的总数量和总价格
                order.total_count = total_count
                order.total_price = total_price
                order.save()
                print(order)

                business1 = Bussiness.objects.get(id=business)
                ordersos = OrderSons.objects.create(order=order,
                                         bussiness=business1)

        except:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})

        # 提交事务
        transaction.savepoint_commit(save_id)
        # todo: 清除用户购物车中对应的记录
        conn.hdel(cart_key, *sku_ids)
        # 返回应答
        return JsonResponse({'res': 5, 'message': '创建成功'})


# Ajax post
# 前端传递的参数：订单id（order——id)
class OrderPayView(View):
    """订单支付"""

    def post(self, request):
        """订单支付"""
        # 用户是否登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmag': '用户未登录'})
        # 接收参数
        order_id = request.POST.get('order_id')
        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效订单ID'})
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 业务处理：使用Python SDK接口，调用支付宝的支付接口
        # 初始化
        app_private_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')).read()
        alipay_public_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')).read()
        alipay = AliPay(
            appid="2021000119635108",  # 沙箱应用ID
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,  # App，即项目本身私钥路径，发送消息时使用此私钥加密
            alipay_public_key_string=alipay_public_key_string,  # 支付宝公钥
            sign_type="RSA2",  # RSA 加密方式
            debug=True,  # 默认为False，如果使用沙箱环境应当为True
        )
        # 调用支付接口
        total_pay = order.total_price + order.transit_price
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(total_pay),
            subject='创客花店%s' % order_id,
            return_url=None,
            notify_url=None,
        )
        # 返回应答
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res': 3, 'pay_url': pay_url})


# Ajax post
# 前端传递的参数：订单ID（order_id）
# /order/check
class CheckPayView(View):
    """查看订单支付的结果"""

    def post(self, request):
        """查询支付结果"""
        # 用户是否登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmag': '用户未登录'})
        # 接收参数
        order_id = request.POST.get('order_id')
        # 校验参数
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效订单ID'})
        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          pay_method=3,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单错误'})

        # 业务处理：使用Python SDK接口，调用支付宝的支付接口
        # 初始化
        app_private_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem')).read()
        alipay_public_key_string = open(os.path.join(settings.BASE_DIR, 'apps/order/alipay_public_key.pem')).read()
        alipay = AliPay(
            appid="2021000119635108",  # 沙箱应用ID
            app_notify_url=None,  # 默认回调url
            app_private_key_string=app_private_key_string,  # App，即项目本身私钥路径，发送消息时使用此私钥加密
            alipay_public_key_string=alipay_public_key_string,  # 支付宝公钥
            sign_type="RSA2",  # RSA 加密方式
            debug=True,  # 默认为False，如果使用沙箱环境应当为True
        )

        # 调用支付宝的交易查询接口
        while True:
            response = alipay.api_alipay_trade_query(order_id)

            code = response.get('code')
            if code == '10000' and response.get('trade_status') == 'TRADE_SUCCESS':
                # 支付成功
                # 获取支付宝交易号
                trade_no = response.get('trade_no')
                # 更新订单的状态
                order.trade_no = trade_no
                order.order_status = 4
                order.save()
                return JsonResponse({'res': 3, 'errmsg': '支付成功'})

                # 返回结果
            elif code == '40004' or (code == '10000' and response.get('trade_status') == 'WAIT_BUYER_PAY'):
                import time
                time.sleep(5)
                continue
            else:
                # 支付出错
                return JsonResponse({'res': 4, 'errmsg': '支付失败'})


class CommentView(LoginRequiredMixin, View):
    """订单评论"""

    def get(self, request, order_id):
        """提供评论页面"""
        user = request.user

        # 校验数据
        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order"))

        # 根据订单的状态获取订单的状态标题
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        # 获取订单商品信息
        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            # 计算商品的小计
            amount = order_sku.count * order_sku.price
            # 动态给order_sku增加属性amount,保存商品小计
            order_sku.amount = amount
        # 动态给order增加属性order_skus, 保存订单商品信息
        order.order_skus = order_skus

        # 使用模板
        return render(request, "order_comment.html", {"order": order})

    def post(self, request, order_id):
        """处理评论内容"""
        user = request.user
        # 校验数据
        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order"))

        # 获取评论条数
        total_count = request.POST.get("total_count")
        total_count = int(total_count)

        # 循环获取订单中商品的评论内容
        for i in range(1, total_count + 1):
            # 获取评论的商品的id
            sku_id = request.POST.get("sku_%d" % i)  # sku_1 sku_2
            # 获取评论的商品的内容
            content = request.POST.get('content_%d' % i, '')  # cotent_1 content_2 content_3
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue

            order_goods.comment = content
            order_goods.save()

        order.order_status = 5  # 已完成
        order.save()

        return redirect(reverse("user:order", kwargs={"page": 1}))
