import time

import json5 as json
import asyncio
import re
from typing import List
from singleton import singleton
import platform

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

        self.async_playwright = None
        self.browser = None
        self.context = None

        self.results = {}

        self.use_proxy = None   # 使用v2ray代理

        # 初始化loop环境
        if platform.system() == 'Windows':
            # 如果为win环境
            print(f'设置asyncio.get_event_loop_policy()之前: {type(asyncio.get_event_loop_policy())}')
            from asyncio import (WindowsProactorEventLoopPolicy)
            asyncio.set_event_loop_policy(WindowsProactorEventLoopPolicy())
            print(f'设置asyncio.get_event_loop_policy()之后: {type(asyncio.get_event_loop_policy())}')

        # Urls实例对应的loop(主要用于win下streamlit等特定场景), 后续可以self.loop.run_until_complete(some_async_func(arg1, arg2, ...))
        # self.loop = asyncio.get_event_loop()
        self.loop = asyncio.new_event_loop()

    async def init(
            self,
    ):
        if self.inited:
            return self

        # print('启动chrome: await async_playwright().start()')

        p = await async_playwright().start()
        self.async_playwright = p
        # p = sync_playwright().start()
        # print('启动chrome: await p.chromium.launch(channel="chrome", headless=True)')

        try:
            # 启动浏览器
            # if self.use_proxy:
            dgreen(f'playwright启动 browser-with-proxy: "{Global.playwright_proxy}".')

            self.browser_with_proxy = await p.chromium.launch(
                channel="chrome",
                headless=True,
                proxy=Global.playwright_proxy   # 关于win下报错：A "socket" was not created for HTTP request before 3000ms，查看internet选项的局域网设置中的代理服务器设置，port和该设置一致就行，如shadowsocket是10809而非10808
            )   # 启动chrome
            self.context_with_proxy = await self.browser_with_proxy.new_context()

            # else:
            dgreen('playwright启动 browser.')

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
            status = response.status if response is not None else 404
            result = Url_Content_Parsed_Result(
                status=status,
                html_content='',
                title='',
                raw_text='',                # 通过body.get_text()获得的全部text，肯定正确，但没有换行
                parsed_text='',             # 通过递归调用next(element.strings())获得的全部text，可能存在解析问题，但具有换行
                text_and_media_list=[],
            )
            self.results[url] = asdict(result)

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

    async def get_bing_search_result(self, query, result_num=10, use_proxy=False, show_results_in_one_page=50):
        results = []

        # 获得context
        context = self.context_with_proxy if use_proxy else self.context

        try:
            # 进行搜索
            page = await context.new_page()

            # url = f"https://www.bing.com/search?q={query}&count={show_results_in_one_page}"
            # await page.goto(url)
            # # await page.wait_for_load_state('networkidle', timeout=2000)
            # await page.wait_for_load_state('networkidle', timeout=Global.playwright_bing_search_time_out)
            #
            # # 解析搜索结果
            # # print(f'page: {page}')
            # search_results = await page.query_selector_all('.b_algo h2')
            # # print(f'search_results: {search_results}')

            # Loop through all required pages

            pages_to_scrape = result_num // show_results_in_one_page +1
            i=0
            for page_num in range(0, pages_to_scrape):
                start = page_num * show_results_in_one_page + 1
                url = f"https://www.bing.com/search?q={query}&count={show_results_in_one_page}&first={start}"

                await page.goto(url)
                await page.wait_for_load_state('networkidle', timeout=show_results_in_one_page/30*Global.playwright_bing_search_time_out)

                results_on_page = await page.query_selector_all('.b_algo h2 a')
                for result in results_on_page:
                    title = await result.inner_text()
                    link = await result.get_attribute('href')
                    if i < result_num:
                        results.append({'title': title, 'url': link})
                    i += 1

        except Exception as e:
            dred(f'get_bing_search_result() error: {e}')
            return []

        # i = 0
        # for result in search_results:
        #     i += 1
        #     title = await result.inner_text()
        #     a_tag = await result.query_selector('a')
        #     if not a_tag: continue
        #     url = await a_tag.get_attribute('href')
        #     if not url:
        #         continue
        #
        #     results.append({
        #         'title': title,
        #         'url': url
        #     })

        return results

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

    await asyncio.wait(tasks, timeout=Global.playwright_get_url_content_time_out)

    await urls_content_retriever.close()
    return results_text_dict

async def async_quick_get_bing_search_result(query,use_proxy=False, result_num=10, show_results_in_one_page=50):
    urls_content_retriever = Urls_Content_Retriever()
    await urls_content_retriever.init()

    results = await urls_content_retriever.get_bing_search_result(query,use_proxy=use_proxy, result_num=result_num, show_results_in_one_page=show_results_in_one_page)

    await urls_content_retriever.close()
    return results

def quick_get_bing_search_result(query,use_proxy=False, result_num=10, show_results_in_one_page=50):
    urls_content_retriever = Urls_Content_Retriever()
    async def _quick_get_bing_search_result(query,use_proxy=False, result_num=result_num, show_results_in_one_page=50):
        await urls_content_retriever.init()

        results = await urls_content_retriever.get_bing_search_result(query,use_proxy=use_proxy, result_num=result_num, show_results_in_one_page=show_results_in_one_page)

        await urls_content_retriever.close()
        return results


    results = urls_content_retriever.loop.run_until_complete(_quick_get_bing_search_result(query,use_proxy=use_proxy, result_num=result_num, show_results_in_one_page=show_results_in_one_page))
    return results

async def async_quick_get_urls_resource_list(urls, res_type_list=['video', 'image', 'text'], use_proxy=False):
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

    await asyncio.wait(tasks, timeout=Global.playwright_get_url_content_time_out)

    await urls_content_retriever.close()
    return results_dict

def quick_get_urls_resource_list(urls, res_type_list=['video', 'image', 'text'], use_proxy=False):
    urls_content_retriever = Urls_Content_Retriever()

    async def _quick_get_urls_resource_list(urls, res_type_list=['video', 'image', 'text'], use_proxy=False):
        # dgreen(f'urls: {urls}')
        # dgreen(f'res_type_list: {res_type_list}')
        # dgreen(f'use_proxy: {use_proxy}')
        results_dict = {
            # 'url': res_list
        }

        tasks = []
        await urls_content_retriever.init()

        async def _get_url_res(url, use_proxy=False):
            await urls_content_retriever.parse_url_content(url, use_proxy=use_proxy)
            results_dict[url] = urls_content_retriever.get_parsed_resource_list(url, res_type_list=res_type_list)

        for url in urls:
            tasks.append(asyncio.create_task(_get_url_res(url, use_proxy=use_proxy)))

        await asyncio.wait(tasks, timeout=Global.playwright_get_url_content_time_out)

        await urls_content_retriever.close()
        return results_dict

    # print(f'urls: {urls}')
    # print(f'res_type_list: {res_type_list}')
    # print(f'use_proxy: {use_proxy}')
    results_dict = urls_content_retriever.loop.run_until_complete(_quick_get_urls_resource_list(urls, res_type_list, use_proxy))
    # print(f'results_dict: {results_dict}')

    return results_dict

surl1 = 'https://www.xvideos.com/tags/porn'
surl2 = 'https://www.xvideos.com/video.mdvtou3e47/eroticax_couple_s_porn_young_love'
surl3 = 'https://www.xvideos.com/tags/porn'
surl4 = 'https://cn.nytimes.com/opinion/20230214/have-more-sex-please/'
url1 = 'https://mp.weixin.qq.com/s/DFIwiKvnhERzI-QdQcZvtQ'
url2 = 'http://www.news.cn/politics/leaders/20240703/3f5d23b63d2d4cc88197d409bfe57fec/c.html'
url3 = 'http://www.news.cn/politics/leaders/20240613/a87f6dec116d48bbb118f7c4fe2c5024/c.html'
url4 = 'http://www.news.cn/politics/xxjxs/index.htm'

async def async_main():
    res_list = await async_quick_get_urls_resource_list([surl1, url2], res_type_list=['video', 'image', 'text'], use_proxy=True)

    print('links1:')
    if surl1 in res_list:
        for item in res_list[surl1]:
            print(item)
    print('links2:')
    if url2 in res_list:
        for item in res_list[url2]:
            print(item)

def sync_main():
    res_list = quick_get_urls_resource_list([surl1, url2], res_type_list=['video', 'image', 'text'], use_proxy=True)
    # res_list = await quick_get_urls_resource_list([surl1, url2], res_type_list=['video', 'image', 'text'], use_proxy=True)

    print('links1:')
    if surl1 in res_list:
        for item in res_list[surl1]:
            print(item)
    print('links2:')
    if url2 in res_list:
        for item in res_list[url2]:
            print(item)

async def async_search_main():
    results = await async_quick_get_bing_search_result(query='李白是谁？', use_proxy=False)
    for item in results:
        print(f"{item['title']}: {item['url']}")

def sync_search_main():
    results = quick_get_bing_search_result(query='霍去病', result_num=200, use_proxy=False)
    results = [item['url'] for item in results]
    for i, item in enumerate(results):
        print(f"{i+1:>2d}) {item}")
        # print(f"{i+1:>2d}) {item['title']}: {item['url']}")

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
    # sync_main()

    sync_search_main()
    # asyncio.run(async_search_main())

    # asyncio.run(async_main())
    # bs4_test()