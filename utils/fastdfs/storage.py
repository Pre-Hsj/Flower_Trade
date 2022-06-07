from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client, get_tracker_conf
from django.conf import settings

class FastDFSStorage(Storage):
    """FastDFS 文件存储类"""
    def __init__(self, client_conf=None, base_url=None):
        """进行初始化"""
        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF
        self.client_conf = client_conf

        if base_url is None:
            base_url = settings.FDFS_URL
        self.base_url = base_url


    def _open(self, name, mode='rb'):
        pass

    def _save(self, name, content):
        """保存文件使用"""
        # name:你选择的上传文件的名字
        # content:包含你上传文件内容的file对象

        # 创建一个Fdfs_client 对象
        client_conf = get_tracker_conf(self.client_conf)
        client = Fdfs_client(client_conf)
        # 上传文件到系统中
        res = client.upload_by_buffer(content.read())
        if res.get('Status') != 'Upload successed.':
            raise Exception('上传文件到Fast DFS失败')
            print('')
        else:
            # 获取返回的文件id
            filename = res.get('Remote file_id')
            return filename.decode()

    def exists(self, name):
        """Django 判断新文件名是否可用"""
        return False

    def url(self, name):
        return self.base_url+name;
