from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from django_redis import get_redis_connection
from utils.mixin import LoginRequiredMixin
# Create your views here.
# 添加商品到购物车
# 1）请求方式：ajax post
# 如果涉及到数据的获取（新增，更新，删除），采用post
# 如果只涉及到数据的获取，采用get
# 2）传递参数：商品id（sku_id） 商品数量（count）
from apps.goods.models import GoodsSKU


class CartAddView(View):
    """购物车记录添加"""

    def post(self, request):
        """购物车记录添加"""
        # 接收数据
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        # 数据校验
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验添加的商品数量
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '商品数目出错'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        # 业务处理：添加购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        # 先尝试获取sku_id的值->hget
        cart_count = conn.hget(cart_key, sku_id)
        if cart_count:
            # 累加购物车中商品数
            count += int(cart_count)
        # 设置hash中sku_id对应的值,sku_id 存在为更新，不存在为新增
        # 校验商品库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})
        conn.hset(cart_key, sku_id, count)
        # 计算用户购物车中的条目数
        total_count = conn.hlen(cart_key)

        # 返回应答
        return JsonResponse({'res': 5, 'total_count': total_count, 'errmsg': '添加成功'})


class CartInfoView(LoginRequiredMixin, View):
    """购物车页面显示"""

    def get(self, request):
        # 获取用户购物车中商品的信息
        # 获取登录用户
        user = request.user
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id
        cart_dict = conn.hgetall(cart_key)
        skus = []
        total_count = 0
        total_price = 0
        for sku_id, count in cart_dict.items():
            sku = GoodsSKU.objects.get(id = sku_id)
            # 计算商品的小计
            amount = sku.price*int(count)
            # 保存商品的小计
            sku.amount = amount
            # 保存购物车中对应的商品数量
            sku.count = count.decode()
            skus.append(sku)
            # 累加计算商品总数目和总价格
            total_count += int(count)
            total_price += amount

        # 组织上下文
        contex = {
            'total_count': total_count,
            'total_price': total_price,
            'skus': skus,
        }
        return render(request, 'cart.html', contex)


# 更新购物车请求
# 采用Ajax的post请求
# 前端需要传递商品id（sku_id） 更新的商品数量（count）
# carts/update
class CartUpdateView(View):
    """购物车记录更新"""

    def post(self, request):
        """购物车记录更新"""
        # 接收数据
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        # 数据校验
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验添加的商品数量
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '商品数目出错'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        # 业务处理：添加购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        # 校验商品库存
        if count > sku.stock:
            return  JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        # 更新
        conn.hset(cart_key, sku_id, count)

        # 计算用户购物车中的商品的总件数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        # 返回应答
        return JsonResponse({'res': 5, 'total_count': total_count, 'message': '更新成功'})


# 删除购物车记录
# 采用ajax post请求
# 前端需要传递的参数：商品的id
# carts/delete
class CartDeleteView(View):
    """购物车记录删除"""
    def post(self, request):
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        sku_id = request.POST.get('sku_id')

        # 数据校验
        if not sku_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的商品id'})
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except:
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

        # 业务处理：删除购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id
        # 删除
        conn.hdel(cart_key, sku_id)
        return JsonResponse({'res': 3, 'message': '删除成功'})
