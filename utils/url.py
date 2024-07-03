from urllib.parse import urlparse, urlunparse

# http://www.news.cn/politics/leaders/20240613/a87f6dec116d48bbb118f7c4fe2c5024/c.html
# 变为
# http://www.news.cn/politics/leaders/20240613/a87f6dec116d48bbb118f7c4fe2c5024
def remove_rightmost_path(url):
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.rsplit('/', 1)
    new_path = path_parts[0] if len(path_parts) > 1 else parsed_url.path
    new_url_parts = parsed_url._replace(path=new_path)
    new_url = urlunparse(new_url_parts)
    return new_url