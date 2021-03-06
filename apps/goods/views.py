from django.shortcuts import render, redirect, reverse
from django.views.generic import View
from django.core.cache import cache

from apps.bussiness.models import Bussiness
from apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner, GoodsSKU
from apps.order.models import OrderGoods
from django_redis import get_redis_connection
from django.core.paginator import Paginator


# Create your views here.
def index(request):
    return render(request, 'index.html')


class IndexView(View):
    """首页"""

    def get(self, request):
        """显示首页"""
        # 尝试从缓存中获取数据
        contex = cache.get('index_page_data')
        if contex is None:
            print("设置缓存")
            # 获取商品的种类信息
            types = GoodsType.objects.all()

            # 获取首页轮播商品信息
            goods_banners = IndexGoodsBanner.objects.all().order_by('index')

            # 获取首页促销活动信息
            promotiom_banners = IndexPromotionBanner.objects.all().order_by('index')

            # 获取首页分类商品展示信息
            for type in types:
                # 获取type种类首页分类商品的图片展示信息
                image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
                # 获取type种类首页分类商品的文字展示信息
                title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')
                # 动态增加属性，分别保存首页分类的图片展示信息和文字展示信息
                type.image_banners = image_banners
                type.title_banners = title_banners

            # 设置缓存
            contex = {
                'types': types,
                'goods_banners': goods_banners,
                'promotion_banners': promotiom_banners
            }
            cache.set('index_page_data', contex, 3600)
            # 获取用户购物车中商品的数目
            # 1.什么时候添加购物车记录：当用户点击加入购物车时需要添加购物车记录
            # 2.什么时候需要获取购物车记录：使用到购物车中的数据和访问购物车页面的时候
            # 3.使用什么存储购物车记录：redis存储购物车记录
            # 4.分析存储购物车记录的格式（hash）：一个用户的购物车记录用一条数据保存，‘cart_用户id’：{‘sku_id’：‘商品数目’}
            # 5.获取用户购物车中的商品条目：hlen
        user = request.user
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)
        else:
            cart_count = 0

        # 组织模板上下文
        contex.update(cart_count=cart_count)
        return render(request, 'index.html', contex)


# /goods/商品id
class DetailView(View):
    """详情页"""

    def get(self, request, goods_id):
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            return redirect(reverse('goods:index'))

        # 获取商品分类信息
        types = GoodsType.objects.all()

        # 获取商品的评论信息
        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment='')

        # 获取商品所属的商家信息
        business = Bussiness.objects.get(id=sku.business)

        # 获取同一个SPU的其他规格的商品信息
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)
        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]

        # 获取购物车信息
        user = request.user
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

            # 添加用户的历史浏览记录
            conn = get_redis_connection('default')
            history_key = 'history_%d' % user.id
            # 移除列表中的goods_id
            conn.lrem(history_key, 0, goods_id)
            # 从左侧插入
            conn.lpush(history_key, goods_id)
            # 只保存用户最新浏览的5条信息
            conn.ltrim(history_key, 0, 4)

        else:
            cart_count = 0

        # 组织上下文
        contex = {
            'sku': sku,
            'types': types,
            'sku_orders': sku_orders,
            'new_skus': new_skus,
            'cart_count': cart_count,
            'same_spu_skus': same_spu_skus,
            'business':business,
        }
        return render(request, 'detail.html', contex)


# 种类id 页码 排序方式
# list/种类id/页码？sort=排序方式
# restful api->请求一种资源（flask）
class ListView(View):
    """列表页"""

    def get(self, request, type_id, page):
        # 获取种类信息goods_type
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            return redirect(reverse('goods:index'))
        # 获取排序方式
        # sort=default，按照默认id排序；sort=price，按照价格排序；sort=hot，按照人气排序
        sort = request.GET.get('sort')
        print(sort)
        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            # 默认方式default
            sort = 'default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')
        # 获取商品的分类信息
        types = GoodsType.objects.all()

        # 对数据进行分页
        paginator = Paginator(skus, 5)

        # 获取第page页的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1

        # 获取第page页的page实例对象
        skus_page = paginator.page(page)
        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]

        # 获取购物车信息
        user = request.user
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

        else:
            cart_count = 0

        # 组织模板的上下文
        contex = {
            'type': type,
            'types': types,
            'skus_page': skus_page,
            'new_skus': new_skus,
            'cart_count': cart_count,
            'sort': sort
        }

        return render(request, 'list.html', contex)
