import time

import json5 as json
import asyncio
import re
from typing import List
from singleton import singleton

from playwright.async_api import async_playwright   # playwright install
from bs4 import BeautifulSoup, Tag                  # pip install playwright beautifulsoup4 lxml
from dataclasses import dataclass, asdict, field
from typing import Any

from config import dred, dgreen, dblue, Global
from tools.retriever.legacy_wrong_html2text import html2text
from utils.url import remove_rightmost_path
from utils.url import get_domain
from utils.decorator import timer

@dataclass
class Url_Content_Parsed_Result():
    status:Any = None
    html_content:Any = None
    title:Any = None
    raw_text:Any = None             # 通过body.get_text()获得的全部text，肯定正确，但没有换行
    parsed_text:Any = None          # 通过递归调用next(element.strings())获得的全部text，可能存在解析问题，但具有换行
    text_and_media_list:Any = None  # 'type'为 'image' | 'video' | 'text'

# @singleton
class Urls_Content_Retriever():
    def __init__(
            self,
    ):
        self.inited = False

        self.loop = None    # Urls实例对应的loop(主要用于win下streamlit等特定场景)

        self.async_playwright = None
        self.browser = None
        self.context = None

        self.results = {}

        self.use_proxy = None   # 使用v2ray代理

    async def init(
            self,
    ):
        if self.inited:
            return self

        print('启动chrome: await async_playwright().start()')

        p = await async_playwright().start()
        self.async_playwright = p
        # p = sync_playwright().start()
        print('启动chrome: await p.chromium.launch(channel="chrome", headless=True)')

        try:
            # 启动浏览器
            # if self.use_proxy:
            dred(f'playwright启动 browser-with-proxy: "{Global.playwright_proxy}".')

            self.browser_with_proxy = await p.chromium.launch(
                channel="chrome",
                headless=True,
                proxy=Global.playwright_proxy   # 关于win下报错：A "socket" was not created for HTTP request before 3000ms，查看internet选项的局域网设置中的代理服务器设置，port和该设置一致就行，如shadowsocket是10809而非10808
            )   # 启动chrome
            self.context_with_proxy = await self.browser_with_proxy.new_context()

            # else:
            dred('playwright启动普通browser.')

            self.browser = await p.chromium.launch(
                channel="chrome",
                headless=True
            )   # 启动chrome

            self.context = await self.browser.new_context()

            print('playwright启动完毕, context已获得.')
        except Exception as e:
            dred(f"Error during browser initialization: {e}")

        self.inited = True
        return self

    async def __aenter__(self):
        dgreen('__aenter__() try to init.')
        return await self.init()

    async def __aexit__(
            self,
            exc_type,       # The type of the exception (e.g., ValueError, RuntimeError).
            exc_val,        # The exception instance itself.
            exc_tb          # The traceback object. （这三个参数必须写，否则报错：TypeError: Urls_Content_Retriever.__aexit__() takes 1 positional argument but 4 were given）
    ):
        dgreen('__aexit__() try to close.')
        await self.close()

    async def close(self):
        if self.context:
            await self.context.close()
        if self.context_with_proxy:
            await self.context_with_proxy.close()
        if self.browser:
            await self.browser.close()
        if self.browser_with_proxy:
            await self.browser_with_proxy.close()
        if self.async_playwright:
            await self.async_playwright.stop()  # 如果没有stop，会报错：ValueError: I/O operation on closed pipe

    # async def _get_raw_pages(self, urls):
    #     # 封装异步任务
    #     tasks = []
    #     for url in urls:
    #         tasks.append(asyncio.create_task(self.parse_url_content(self.context, url)))
    #
    #     await asyncio.wait(tasks, timeout=100)
    #
    #     return self.results

    # def _html_2_text_paras(self, html: str) -> List[str]:
    #     if html is None:
    #         return []
    #
    #     paras = html2text(html).split("\n")
    #     paras = self._pre_filter(paras)
    #     return paras

    # def _pre_filter(self, paragraphs):
    #     # sorted_paragraphs = sorted(paragraphs, key=lambda x: len(x))
    #     # if len(sorted_paragraphs[-1]) < 10:
    #     #     return []
    #     ret = []
    #     for item in paragraphs:
    #         item = item.strip()
    #         item = re.sub(r"\[\d+\]", "", item)
    #         if len(item) < 50:
    #             continue
    #         if len(item) > 1200:
    #             item = item[:1200] + "..."
    #         ret.append(item)
    #     return ret

    def get_parsed_text(self, url, raw_text=True):
        text =  self.results[url]['raw_text'] if raw_text else self.results[url]['parsed_text']
        return text

    def get_parsed_resource_list(self, url, res_type_list=['video', 'image', 'text']):
        res_list =  self.results[url]['text_and_media_list']
        rtn_list = []
        for item in res_list:
            if item['type'] in res_type_list:
                rtn_list.append(item)
        return rtn_list

    # 将url的text、img、video等内容解析出来
    async def parse_url_content(
            self,
            url,
            use_proxy=False,
    ):


        dgreen(f'获取网页"{url}"的内容...')
        response = None

        try:
            self.results[url] = [None, None]

            context = self.context_with_proxy if use_proxy else self.context
            response = await context.request.get(
                url,
                timeout=Global.playwright_get_url_content_time_out,
            )

            html_content = await response.text()
            raw_text = await self._html_to_text(html_content)
            title, parsed_text, text_and_media_list = await self._get_text_and_media(html_content, url)
            # print(f'text_media: {text_media}')

            result = Url_Content_Parsed_Result(
                status=response.status,
                html_content=html_content,
                title=title,
                raw_text=raw_text,              # 通过body.get_text()获得的全部text，肯定正确，但没有换行
                parsed_text=parsed_text,        # 通过递归调用next(element.strings())获得的全部text，可能存在解析问题，但具有换行
                text_and_media_list=text_and_media_list,
            )
            self.results[url] = asdict(result)

        except Exception as e:
            dred(f'_get_url_content() error: {e}')
            if response is not None:
                self.results[url] = (response.status, '')
            else:
                self.results[url] = (404, '获取网页内容失败.')

    async def _html_to_text(self, html):
        # 使用 BeautifulSoup 解析 HTML 并提取正文
        soup = BeautifulSoup(html, 'html.parser')

        # 提取正文内容
        # 你可以根据实际情况调整选择器
        body = soup.find('body')  # 获取页面的 <body> 内容
        # paragraphs = body.find_all('p') if body else []  # 获取所有 <p> 标签内容

        # 获取body下完整的文本
        # text_content = body.get_text(strip=True)

        text_content = body.get_text(separator='\n',strip=True)

        # print(f'text_content:{text_content}')
        return text_content

    async def _get_text_and_media(self, html, url) -> list:
        # 使用 BeautifulSoup 解析 HTML 并提取正文
        soup = BeautifulSoup(html, 'html.parser')

        extracted_content_list = []
        extracted_title = ''
        extracted_text_list = []

        title_tag = soup.find('title')
        title = title_tag.get_text() if title_tag else ''
        title = title.strip()
        extracted_content_list.append({'type': 'title', 'content': title})
        extracted_title = title

        body = soup.find('body')

        # 准备提取的内容列表

        # 定义一个递归函数，用于遍历并提取文本和媒体元素
        def _extract_elements(element):
            not_needed = Global.playwright_url_content_not_needed
            def foo():
                pass

            # print(f'---------------element: {element}---------------')
            if isinstance(element, Tag):
                if element.name == 'div' or element.name == 'p' or element.name == 'span':
                    text = ''
                    try:
                        text = next(element.strings).strip()    # 获取<div>、<p>、<span>等标签后面的文本，但可能获取到<div><p>text1</p></div>的<div>的text1，导致div和p重复获取text1
                    except StopIteration:
                        pass
                    finally:
                        if text and (not element.find_all('p')) and (not element.find_all('span')):
                            extracted_content_list.append({'type': 'text', 'raw_type':element.name, 'content':text})
                            extracted_text_list.append(text)
                if element.name == 'img':
                    # print(f'---------------img element: {element}---------------')
                    # src的图片
                    img_src = element.get('src')
                    if img_src:
                        if not img_src.startswith(('http://', 'https://')): # 如果是相对路径，将其转换为绝对路径
                            img_src = f"{get_domain(url)}/{img_src.lstrip('/')}"
                        extracted_content_list.append({'type': 'image', 'raw_type':'src', 'content': img_src})
                    # data-src的图片
                    img_src = element.get('data-src')
                    if img_src:
                        if not img_src.startswith(('http://', 'https://')): # 如果是相对路径，将其转换为绝对路径
                            img_src = f"{remove_rightmost_path(url.rstrip('/'))}/{img_src.lstrip('/')}"
                        extracted_content_list.append({'type': 'image', 'raw_type':'data-src', 'content': img_src})
                elif element.name == 'video':
                    # print(f'---------------video element: {element}---------------')
                    src = element.get('src')
                    if src:
                        if not src.startswith(('http://', 'https://')):  # 如果是相对路径，将其转换为绝对路径
                            src = f"{get_domain(url)}/{src.lstrip('/')}"
                        extracted_content_list.append({'type': 'video', 'content': src})
                    else:
                        # 查找 <source> 标签中的视频链接
                        sources = element.find_all('source')
                        video_sources = [source.get('src') for source in sources if source.get('src')]
                        if video_sources:
                            extracted_content_list.append({'type': 'video', 'content': video_sources[0]})
                elif element.name == 'a':
                    src = element.get('href')
                    if src and ('mp4' in src or 'video' in src):
                        # print(f'---------------video element: {element}---------------')
                        if not src.startswith(('http://', 'https://')):  # 如果是相对路径，将其转换为绝对路径
                            src = f"{get_domain(url)}/{src.lstrip('/')}"
                        extracted_content_list.append({'type': 'video', 'content': src})
                    else:
                        # 查找 <source> 标签中的视频链接
                        sources = element.find_all('source')
                        video_sources = [source.get('src') for source in sources if source.get('src')]
                        if video_sources:
                            extracted_content_list.append({'type': 'video', 'content': video_sources[0]})
                # else:
                # 继续递归遍历其他嵌套元素
                for child in element.children:
                    _extract_elements(child)
            elif isinstance(element, str):
                pass
                # 添加非标签字符串文本
                # extracted_content_list.append({'type': 'text', 'content': element})

            # return found

        # 从 body 元素开始提取内容
        if body:
            _extract_elements(body)

        return extracted_title, '\n'.join(extracted_text_list), extracted_content_list

    # page.goto(url)的方式，速度很慢
    # async def _legacy_get_page_content(self, url: str) -> str:
    #     async with async_playwright() as p:
    #         browser = await p.chromium.launch(headless=True)  # 你可以将 headless=True 改为 False 以查看浏览器操作
    #         page = await browser.new_page()
    #         await page.goto(url)
    #         content = await page.content()  # 获取页面的 HTML 内容
    #         await browser.close()
    #
    #         # 使用 BeautifulSoup 解析 HTML 并提取正文
    #         soup = BeautifulSoup(content, 'html.parser')
    #
    #         # 提取正文内容
    #         # 你可以根据实际情况调整选择器
    #         body = soup.find('body')  # 获取页面的 <body> 内容
    #         paragraphs = body.find_all('p') if body else []  # 获取所有 <p> 标签内容
    #
    #         # 将所有段落的文本合并成一个字符串
    #         text_content = '\n'.join([p.get_text() for p in paragraphs])
    #
    #         return text_content


async def quick_get_url_text(url, use_proxy=False):
    urls_content_retriever = Urls_Content_Retriever()
    await urls_content_retriever.init()

    await urls_content_retriever.parse_url_content(url, use_proxy=use_proxy)

    result_text =  urls_content_retriever.get_parsed_text(url)
    await urls_content_retriever.close()

    return result_text

async def quick_get_urls_text(urls, use_proxy=False, raw_text=True):
    results_text_dict = {
        # 'url': text
    }

    tasks = []
    urls_content_retriever = Urls_Content_Retriever()
    await urls_content_retriever.init()

    async def _get_url_text(url, use_proxy=False):
        await urls_content_retriever.parse_url_content(url, use_proxy=use_proxy)
        results_text_dict[url] = urls_content_retriever.get_parsed_text(url, raw_text=raw_text)

    for url in urls:
        tasks.append(asyncio.create_task(_get_url_text(url, use_proxy=use_proxy)))

    await asyncio.wait(tasks, timeout=3000)

    await urls_content_retriever.close()
    return results_text_dict

async def quick_get_urls_resource_list(urls, res_type_list=['video', 'image', 'text'], use_proxy=False):
    results_dict = {
        # 'url': res_list
    }

    tasks = []
    urls_content_retriever = Urls_Content_Retriever()
    await urls_content_retriever.init()

    async def _get_url_res(url, use_proxy=False):
        await urls_content_retriever.parse_url_content(url, use_proxy=use_proxy)
        results_dict[url] = urls_content_retriever.get_parsed_resource_list(url, res_type_list=res_type_list)

    for url in urls:
        tasks.append(asyncio.create_task(_get_url_res(url, use_proxy=use_proxy)))

    await asyncio.wait(tasks, timeout=3000)

    await urls_content_retriever.close()
    return results_dict

async def main():
    surl1 = 'https://www.xvideos.com/tags/porn'
    surl2 = 'https://www.xvideos.com/video.mdvtou3e47/eroticax_couple_s_porn_young_love'
    surl3 = 'https://www.xvideos.com/tags/porn'
    surl4 = 'https://cn.nytimes.com/opinion/20230214/have-more-sex-please/'
    url1 = 'https://mp.weixin.qq.com/s/DFIwiKvnhERzI-QdQcZvtQ'
    url2 = 'http://www.news.cn/politics/leaders/20240703/3f5d23b63d2d4cc88197d409bfe57fec/c.html'
    url3 = 'http://www.news.cn/politics/leaders/20240613/a87f6dec116d48bbb118f7c4fe2c5024/c.html'
    url4 = 'http://www.news.cn/politics/xxjxs/index.htm'

    res_list = await quick_get_urls_resource_list([surl1, url2], res_type_list=['video', 'image', 'text'], use_proxy=True)

    print('links1:')
    for item in res_list[surl1]:
        print(item)
    print('links2:')
    for item in res_list[url2]:
        print(item)

def bs4_test():
    from bs4 import BeautifulSoup

    html = '''<div><p>This is a paragraph1.</p>
    <p>This is a paragraph2.</p>
    <p>This is a paragraph3.</p>
    <p>This is a paragraph4.</p>
    And some more text.
</div>
'''

    soup = BeautifulSoup(html, 'html.parser')
    div = soup.div

    print('[origin]')
    print(f"'{html}'")

    # 方法 1
    print('[1]')
    print(div.string)  # 这会返回 None，因为 div 有多个子节点
    print(f'{next(div.strings).strip()!r}')  # 这会返回 None，因为 div 有多个子节点
    # print('text'!r)

    # 方法 2
    print('[2]')
    print(f'"{div.get_text(strip=True)}"')
    print(f'"{div.get_text(strip=False)}"')

    # 方法 3
    print('[3]')
    print(''.join(child for child in div.contents if isinstance(child, str)).strip())

    # 方法 4
    print('[4]')
    print(' '.join(div.find_all(text=True, recursive=False)).strip())

if __name__ == '__main__':
    asyncio.run(main())
    # bs4_test()