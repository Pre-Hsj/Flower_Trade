# 使用celery
from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
from django.template import loader, RequestContext
# 创建一个Celery的实例对象
from django_redis import get_redis_connection
# 定义任务函数
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Flower_Trade.settings")
django.setup()
from apps.goods.models import IndexGoodsBanner, IndexTypeGoodsBanner, IndexPromotionBanner, GoodsType

app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/1')


@app.task
def send_register_active_email(to_email, username, token):
    """发送激活邮件"""
    subject = '创客花店欢迎信息'
    message = ""
    html_message = '<h1>%s,欢迎您成为创客花店注册会员<h1>请点击下面链接激活您的账户<br/><a ' \
                   'href=http://127.0.0.1:8000/user/active/%s>http://127.0.0.1:8000/user/active/%s</a>' % (
                       username, token, token)
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    send_mail(subject, message, sender, receiver, html_message=html_message)

@app.task(name='')
def send_register_active_email_business(to_email, bussiness_name, token):
    """发送激活邮件"""
    subject = '创客花店欢迎信息'
    message = ""
    html_message = '<h1>%s,欢迎您成为创客花店注册商家<h1>请点击下面链接激活您的账户<br/><a ' \
                   'href=http://127.0.0.1:8000/bussiness/active/%s>http://127.0.0.1:8000/bussiness/active/%s</a>' % (
                       bussiness_name, token, token)
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    send_mail(subject, message, sender, receiver, html_message=html_message)

# 首页页面的静态化：当管理员修改首页信息对应的表格中的数据的时候，需要重新生成静态页面
@app.task()
def generate_index_html():
    """产生首页静态页面"""
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
        # 组织模板上下文
        contex = {
            'types': types,
            'goods_banners': goods_banners,
            'promotion_banners': promotiom_banners,
        }

        # 使用模板：加载模板文件，定义模板上下文，模板渲染
        temp = loader.get_template('static_index.html')
        # contex = RequestContext(request, contex)
        static_index_html = temp.render(contex)

        # 生成首页对应的静态文件
        save_path = os.path.join(settings.BASE_DIR, 'static/static_index.html')
        with open(save_path, 'w', encoding='UTF-8') as f:
            f.write(static_index_html)
