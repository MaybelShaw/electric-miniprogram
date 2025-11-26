from django.core.files.storage import FileSystemStorage
from django.conf import settings


class LocalMediaStorage(FileSystemStorage):
    """
    开发环境本地文件存储，基于 FileSystemStorage。
    - 读写目录：settings.MEDIA_ROOT
    - 基础URL：settings.MEDIA_URL
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('location', str(settings.MEDIA_ROOT))
        kwargs.setdefault('base_url', settings.MEDIA_URL)
        super().__init__(*args, **kwargs)