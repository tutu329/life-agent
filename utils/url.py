from urllib.parse import urlparse, urlunparse
import urllib.parse

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

def get_domain(url):
    # 输入的完整URL
    # input_url = "https://github.com/search?q=repo%3ANanmiCoder%2FMediaCrawler+sns-video-qc.xhscdn.com&type=code"
    # output = "https://github.com/"
    # 解析URL
    parsed_url = urllib.parse.urlparse(url)

    # 替换成根URL
    output_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # print(output_url)
    return output_url

def main():
    print(get_domain('https://github.com/search?q=repo%3ANanmiCode'))

if __name__ == '__main__':
    main()