import sanic
from packaging.version import Version

__title__ = ' Sanic RESTful Framework'
__version__ = '0.0.2'
__author__ = 'Chacer'
__author_email__ = '1364707405c@gmail.com'

if Version(sanic.__version__) < Version("25.0.0"):
    raise ImportError("It's never been tested with sanic version earlier than 25.0.0")
