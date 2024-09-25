import time

import json5 as json
import asyncio
import re
from typing import List
from singleton import singleton
import platform

from playwright.sync_api import sync_playwright
from playwright.async_api import async_playwright   # playwright install
from bs4 import BeautifulSoup, Tag                  # pip install playwright beautifulsoup4 lxml
from dataclasses import dataclass, asdict, field
from typing import Any

from config import dred, dgreen, dblue, Global
from tools.retriever.legacy_wrong_html2text import html2text
from utils.url import remove_rightmost_path
from utils.url import get_domain_of_url
from utils.string_util import str_replace_multiple_newlines_with_one_newline
from utils.decorator import timer
from utils.url import get_clean_html

from playwright.async_api import TimeoutError as Playwright_TimeoutError

# 提供User-Agent的模拟数据
from fake_useragent import UserAgent    # pip install fake-useragent

from tools.llm.api_client import Concurrent_LLMs

@dataclass
class Text_and_Media():
    type:       Any = None      # 'type'为 'image' | 'video' | 'text'
    raw_type:   Any = None      # 'raw_type'为 element.name | 'src' | 'data-src'
    content:    Any = None      # 'content'为 text | url_link

@dataclass
class Url_Content_Parsed_Result():
    status:                 Any = None
    html_content:           Any = None
    title:                  Any = None
    # raw_text:               Any = None              # 通过body.get_text()获得的全部text，肯定正确，但没有换行
    parsed_text:            Any = None              # 通过递归调用next(element.strings())获得的全部text，可能存在解析问题，但具有换行
    text_and_media_list:    Text_and_Media = None

# @singleton
class Urls_Content_Retriever():
    def __init__(
            self,
    ):
        self.inited = False

        self.async_playwright = None

        self.browser_with_proxy = None
        self.browser = None
        self.context = None

        self.results = {}

        self.use_proxy = None   # 使用v2ray代理

        # 初始化loop环境
        if platform.system() == 'Windows':
            # 如果为win环境
            dgreen(f'[Urls_Content_Retriever] os为Windows. 设置set_event_loop_policy()之前: {type(asyncio.get_event_loop_policy())}')
            from asyncio import (WindowsProactorEventLoopPolicy)
            asyncio.set_event_loop_policy(WindowsProactorEventLoopPolicy())
            dgreen(f'[Urls_Content_Retriever] os为Windows. 设置set_event_loop_policy()之后: {type(asyncio.get_event_loop_policy())}')

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
            dgreen(f'[Urls_Content_Retriever] playwright启动 browser1(with-proxy): "{Global.playwright_proxy}".')

            self.browser_with_proxy = await p.chromium.launch(
                channel="chrome",
                headless=False,
                # headless=True,
                proxy=Global.playwright_proxy   # 关于win下报错：A "socket" was not created for HTTP request before 3000ms，查看internet选项的局域网设置中的代理服务器设置，port和该设置一致就行，如shadowsocket是10809而非10808
            )   # 启动chrome
            self.context_with_proxy = await self.browser_with_proxy.new_context(user_agent=UserAgent().random)

            # else:
            dgreen('[Urls_Content_Retriever] playwright启动 browser2(without-proxy).')

            self.browser = await p.chromium.launch(
                channel="chrome",
                headless=False,
                # headless=True,
            )   # 启动chrome

            self.context = await self.browser.new_context(user_agent=UserAgent().random)

            # print('playwright启动完毕, context已获得.')
        except Exception as e:
            dred(f'[Urls_Content_Retriever] Urls_Content_Retriever.Init() error ({type(e)}): "{e}"')

        self.inited = True
        return self

    async def __aenter__(self):
        dgreen('[Urls_Content_Retriever] __aenter__() try to init.')
        return await self.init()

    async def __aexit__(
            self,
            exc_type,       # The type of the exception (e.g., ValueError, RuntimeError).
            exc_val,        # The exception instance itself.
            exc_tb          # The traceback object. （这三个参数必须写，否则报错：TypeError: Urls_Content_Retriever.__aexit__() takes 1 positional argument but 4 were given）
    ):
        dgreen('[Urls_Content_Retriever] __aexit__() try to close.')
        await self.close()

    async def close(self):
        dgreen('[Urls_Content_Retriever] try to close.')
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

    def get_title(self, url):
        return self.results[url]['title']

    def get_parsed_text(self, url):
        # text =  self.results[url]['raw_text'] if raw_text else self.results[url]['parsed_text']
        # if one_new_line:
        #     text = str_replace_multiple_newlines_with_one_newline(text)
        # return text
        text =  self.results[url]['parsed_text']
        return text

    def get_parsed_content_list(self, url, res_type_list=['video', 'image', 'text']):
        res_list =  self.results[url]['text_and_media_list']
        rtn_list = []
        rtn_list.append({'type': 'text', 'raw_type': 'title', 'content': self.results[url]['title'] })
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
        dgreen(f'[Urls_Content_Retriever] 获取网页"{url}"的内容...')
        response = None

        try:
            self.results[url] = [None, None]

            context = self.context_with_proxy if use_proxy else self.context

            # ============获取静态html内容============
            # response = await context.request.get(
            #     url,
            #     timeout=Global.playwright_get_url_content_time_out,
            # )
            # html_content = await response.text()

            # ============获取动态页面的html内容============
            page = await context.new_page()
            # await page.set_extra_http_headers({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
            await page.goto(url)
            # 等待页面加载完成
            await page.wait_for_load_state('networkidle')
            # 获取 <body> 下的文本
            # body_text = page.evaluate('document.body.innerText')
            # 获取html

            html_content = await page.evaluate('() => document.documentElement.outerHTML')
            # print(f'----------------------------------raw html:{html_content}------------------------------')
            # 非常关键的步骤，将html中非正文的部分都清除干净
            title, html_content = get_clean_html(html_content)

            # html_content = await page.inner_text('body')
            # print(f'----------------------------------clean html:{html_content}------------------------------')

            # import chardet
            # print(f"----------------------------------{chardet.detect(html_content)['encoding']}------------------------------")
            # html_content.decode('utf-8')


            # raw_text = await self._html_to_text(html_content)
            parsed_text, text_and_media_list = await self._get_text_and_media(html_content, url)
            # print(f'text_media: {text_media}')

            result = Url_Content_Parsed_Result(
                # status=response.status,
                html_content=html_content,
                title=title,
                # raw_text=raw_text,              # 通过body.get_text()获得的全部text，肯定正确，但没有换行
                parsed_text=parsed_text,        # 通过递归调用next(element.strings())获得的全部text，可能存在解析问题，但具有换行
                text_and_media_list=text_and_media_list,
            )
            self.results[url] = asdict(result)
        except Playwright_TimeoutError as e:
            dred(f'[Urls_Content_Retriever] Playwright_TimeoutError: "{e}"')
            result = Url_Content_Parsed_Result(
                html_content='',
                title='',
                # raw_text='',                # 通过body.get_text()获得的全部text，肯定正确，但没有换行
                parsed_text='',             # 通过递归调用next(element.strings())获得的全部text，可能存在解析问题，但具有换行
                text_and_media_list=[],
            )
            self.results[url] = asdict(result)
        except Exception as e:
            dred(f'[Urls_Content_Retriever] error({type(e)}): "{e}"')
            # status = response.status if response is not None else 404
            result = Url_Content_Parsed_Result(
                # status=status,
                html_content='',
                title='',
                # raw_text='',                # 通过body.get_text()获得的全部text，肯定正确，但没有换行
                parsed_text='',             # 通过递归调用next(element.strings())获得的全部text，可能存在解析问题，但具有换行
                text_and_media_list=[],
            )
            self.results[url] = asdict(result)

    async def _html_to_text(self, html):
        # 使用 BeautifulSoup 解析 HTML 并提取正文
        soup = BeautifulSoup(html, 'html.parser')
        # print(f'soup: {soup}')

        # 提取正文内容
        # 你可以根据实际情况调整选择器
        body = soup.find('body')  # 获取页面的 <body> 内容
        # paragraphs = body.find_all('p') if body else []  # 获取所有 <p> 标签内容

        # 获取body下完整的文本
        # text_content = body.get_text(strip=True)

        # print(f'body: {body}')
        text_content = body.get_text(separator='\n',strip=True) if body is not None else ''

        # print(f'text_content:{text_content}')
        return text_content

    async def _get_text_and_media(self, html, url) -> list:
        # 使用 BeautifulSoup 解析 HTML 并提取正文
        soup = BeautifulSoup(html, 'html.parser')

        extracted_content_list = []
        # extracted_title = ''
        extracted_text_list = []

        # title_tag = soup.find('title')
        # title = title_tag.get_text().strip() if title_tag else ''
        # extracted_content_list.append({'type': 'title', 'content': title})
        # extracted_title = title

        body = soup.find('body')

        # 准备提取的内容列表

        # 定义一个递归函数，用于遍历并提取文本和媒体元素
        def _extract_elements(
                element,
        ):
            def _get_node_direct_text(element):
                return ''.join(text for text in element.find_all(string=True, recursive=False)).strip()

            # print(f'---------------element: {element}---------------')
            if isinstance(element, Tag):
                if element.name in Global.html_text_tags:   # 文本类
                    text = _get_node_direct_text(element)
                    if text:
                        data = Text_and_Media(type='text', raw_type=element.name, content=text)
                        extracted_content_list.append(asdict(data))
                        # extracted_content_list.append({'type': 'text', 'raw_type':element.name, 'content':text})
                        extracted_text_list.append(text)
                if element.name == 'img':
                    # print(f'---------------img element: {element}---------------')
                    # src的图片
                    img_src = element.get('src')
                    if img_src:
                        if not img_src.startswith(('http://', 'https://')): # 如果是相对路径，将其转换为绝对路径
                            img_src = f"{get_domain_of_url(url)}/{img_src.lstrip('/')}"
                        data = Text_and_Media(type='image', raw_type='src', content=img_src)
                        extracted_content_list.append(asdict(data))
                        # extracted_content_list.append({'type': 'image', 'raw_type':'src', 'content': img_src})
                    # data-src的图片
                    img_src = element.get('data-src')
                    if img_src:
                        if not img_src.startswith(('http://', 'https://')): # 如果是相对路径，将其转换为绝对路径
                            img_src = f"{remove_rightmost_path(url.rstrip('/'))}/{img_src.lstrip('/')}"
                        data = Text_and_Media(type='image', raw_type='data-src', content=img_src)
                        extracted_content_list.append(asdict(data))
                        # extracted_content_list.append({'type': 'image', 'raw_type':'data-src', 'content': img_src})
                elif element.name == 'video':
                    # print(f'---------------video element: {element}---------------')
                    src = element.get('src')
                    if src:
                        if not src.startswith(('http://', 'https://')):  # 如果是相对路径，将其转换为绝对路径
                            src = f"{get_domain_of_url(url)}/{src.lstrip('/')}"
                        data = Text_and_Media(type='video', raw_type='src', content=src)
                        extracted_content_list.append(asdict(data))
                        # extracted_content_list.append({'type': 'video', 'content': src})
                    else:
                        # 查找 <source> 标签中的视频链接
                        sources = element.find_all('source')
                        video_sources = [source.get('src') for source in sources if source.get('src')]
                        if video_sources:
                            data = Text_and_Media(type='video', raw_type='src', content=video_sources[0])
                            extracted_content_list.append(asdict(data))
                            # extracted_content_list.append({'type': 'video', 'content': video_sources[0]})
                elif element.name == 'a':
                    src = element.get('href')
                    if src and ('mp4' in src or 'video' in src):
                        # print(f'---------------video element: {element}---------------')
                        if not src.startswith(('http://', 'https://')):  # 如果是相对路径，将其转换为绝对路径
                            src = f"{get_domain_of_url(url)}/{src.lstrip('/')}"
                        data = Text_and_Media(type='video', raw_type='src', content=src)
                        extracted_content_list.append(asdict(data))
                        # extracted_content_list.append({'type': 'video', 'content': src})
                    else:
                        # 查找 <source> 标签中的视频链接
                        sources = element.find_all('source')
                        video_sources = [source.get('src') for source in sources if source.get('src')]
                        if video_sources:
                            data = Text_and_Media(type='video', raw_type='src', content=video_sources[0])
                            extracted_content_list.append(asdict(data))
                            # extracted_content_list.append({'type': 'video', 'content': video_sources[0]})
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
        else:
            dred('[Urls_Content_Retriever] 网页body为空.')

        return '\n'.join(extracted_text_list), extracted_content_list

    async def get_bing_search_result(self, query, result_num=10, use_proxy=False, show_results_in_one_page=50, max_retry=3):
        result_url_list = []

        # 获得context
        context = self.context_with_proxy if use_proxy else self.context

        try:
            # 获取如100+个搜索结果(每页如50个，则翻页num/50+1次)，汇总为list
            pages_to_scrape = result_num // show_results_in_one_page + 1
            i=0
            for page_num in range(0, pages_to_scrape):
                start = page_num * show_results_in_one_page + 1
                url = f"https://www.bing.com/search?q={query}&count={show_results_in_one_page}&first={start}"

                timeout = show_results_in_one_page/30*Global.playwright_bing_search_time_out

                retry_num = 0
                results_on_page = None
                success = False
                page = await context.new_page()
                await page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
                })

                while retry_num < max_retry:
                    try:
                        print(f'try to goto page: "{url}" with use_proxy: "{use_proxy}" with timeout:"{timeout:.1f}ms"')
                        await page.goto(url)
                        # await page.wait_for_timeout(1000)  # 额外等待2秒后重新加载
                        print('完成goto()')
                        # await page.wait_for_load_state('networkidle')
                        # await page.wait_for_load_state('networkidle', timeout=timeout)
                        # await page.wait_for_selector('.b_algo h2 a')
                        await page.wait_for_selector('.b_algo h2 a', timeout=timeout)
                        print('完成wait_for_selector()')
                        # await page.wait_for_selector('.b_algo h2 a')
                        results_on_page = await page.query_selector_all('.b_algo h2 a')
                        print('完成query_selector_all()')
                        # results_on_page = await page.query_selector_all('.b_algo h2 a')
                        if len(results_on_page)>0:
                            success = True
                            break
                        retry_num += 1
                        await page.wait_for_timeout(1000)  # 额外等待2秒后重新加载
                        # await page.reload()
                        page = await context.new_page()
                        dred(f'【get_bing_search_result】 retry_num: {retry_num}')
                    except Playwright_TimeoutError as e:
                        dred(f'【get_bing_search_result】 Playwright_TimeoutError({e})')
                        dred(f'【get_bing_search_result】 retry_num: {retry_num}')
                        retry_num += 1
                        await page.wait_for_timeout(1000)  # 额外等待2秒后重新加载
                        # await page.reload()
                        page = await context.new_page()

                if success:
                    dgreen(f'【get_bing_search_result】 success with results num: {len(results_on_page)}')
                else:
                    dred(f'【get_bing_search_result】 failed.')
                    return []

                for result in results_on_page:
                    title = await result.inner_text()
                    result_url = await result.get_attribute('href')
                    if i < result_num:
                        result_url_list.append(result_url)
                    i += 1

        except Playwright_TimeoutError as e:
            dred(f'[Urls_Content_Retriever] get_bing_search_result() Playwright_TimeoutError: "{e}"')
            return []
        except Exception as e:
            dred(f'[Urls_Content_Retriever] get_bing_search_result() error ({type(e)}): "{e}"')
            return []

        return result_url_list

# 同步：获取url的文本
def get_url_text(url, use_proxy=False):
    ret = Urls_Content_Retriever()
    async def _get_url_text():
        await ret.init()
        await ret.parse_url_content(url, use_proxy=use_proxy)
        result_text = ret.get_title(url) + '\n'
        result_text += ret.get_parsed_text(url)

        await ret.close()
        return result_text

    result_text = ret.loop.run_until_complete(_get_url_text())
    return result_text

# 同步：获取多个urls的文本
def get_urls_text(urls, use_proxy=False)->dict:
    ret = Urls_Content_Retriever()
    async def _get_urls_text():
        results_text_dict = {
            # 'url': text
        }

        tasks = []
        await ret.init()
        async def _get_url_text(url):
            await ret.parse_url_content(url, use_proxy=use_proxy)
            results_text_dict[url] = ret.get_title(url) + '\n'
            results_text_dict[url] += ret.get_parsed_text(url)

        for url in urls:
            tasks.append(asyncio.create_task(_get_url_text(url)))

        await asyncio.wait(tasks, timeout=Global.playwright_get_url_content_time_out)
        await ret.close()
        return results_text_dict

    results_text_dict = ret.loop.run_until_complete(_get_urls_text())
    return results_text_dict

# 同步：获取bing的搜索结果
def get_bing_search_result(query, use_proxy=False, result_num=10, show_results_in_one_page=50):
    ret = Urls_Content_Retriever()
    async def _quick_get_bing_search_result():
        await ret.init()

        results = await ret.get_bing_search_result(query,use_proxy=use_proxy, result_num=result_num, show_results_in_one_page=show_results_in_one_page)

        await ret.close()
        return results

    results = ret.loop.run_until_complete(_quick_get_bing_search_result())
    return results

# 同步：获取多个urls的图文
def get_urls_content_list(urls, res_type_list=['video', 'image', 'text'], use_proxy=False):
    if not urls:
        return {}

    ret = Urls_Content_Retriever()

    async def _get_urls_content_list(urls, res_type_list=['video', 'image', 'text'], use_proxy=False):
        # dgreen(f'urls: {urls}')
        # dgreen(f'res_type_list: {res_type_list}')
        # dgreen(f'use_proxy: {use_proxy}')
        results_dict = {
            # 'url': res_list
        }

        tasks = []
        await ret.init()

        async def _get_url_res(url):
            await ret.parse_url_content(url, use_proxy=use_proxy)
            results_dict[url] = ret.get_parsed_content_list(url, res_type_list=res_type_list)

        for url in urls:
            tasks.append(asyncio.create_task(_get_url_res(url)))

        await asyncio.wait(tasks, timeout=Global.playwright_get_url_content_time_out)
        await ret.close()
        return results_dict

    # print(f'urls: {urls}')
    # print(f'res_type_list: {res_type_list}')
    # print(f'use_proxy: {use_proxy}')
    results_dict = ret.loop.run_until_complete(_get_urls_content_list(urls, res_type_list, use_proxy))
    # print(f'results_dict: {results_dict}')

    return results_dict

def get_url_content_list(url, res_type_list=['video', 'image', 'text'], use_proxy=False):
    res = get_urls_content_list([url], res_type_list=res_type_list, use_proxy=use_proxy)
    return res[url]

async def try_to_get_urls_of_some_search_site(url, result_num=100):
    result_url_list = []

    p = await async_playwright().start()
    browser = await p.chromium.launch(
        channel="chrome",
        headless=True,
        # proxy=Global.playwright_proxy
    )
    context = await browser.new_context(user_agent=UserAgent().random)

    page = await context.new_page()
    await page.goto(url)
    await page.wait_for_load_state('networkidle', timeout=Global.playwright_bing_search_time_out)
    results_on_page = await page.query_selector_all('.opr-toplist1-table_544Ty div div div a')
    # results_on_page = await page.query_selector_all('.ttp-hot-board ol li a')
    print(f'results_on_page: {results_on_page}')

    i=0
    for result in results_on_page:
        title = await result.inner_text()
        result_url = await result.get_attribute('href')
        if i < result_num:
            result_url_list.append(result_url)
        i += 1

    for url in result_url_list:
        print(f'url: https://www.baidu.com{url}')


surl1 = 'https://www.xvideos.com/tags/porn'
surl2 = 'https://www.xvideos.com/video.mdvtou3e47/eroticax_couple_s_porn_young_love'
surl3 = 'https://www.xvideos.com/tags/porn'
surl4 = 'https://cn.nytimes.com/opinion/20230214/have-more-sex-please/'
url1 = 'https://mp.weixin.qq.com/s/DFIwiKvnhERzI-QdQcZvtQ'
url2 = 'http://www.news.cn/politics/leaders/20240703/3f5d23b63d2d4cc88197d409bfe57fec/c.html'
url3 = 'http://www.news.cn/politics/leaders/20240613/a87f6dec116d48bbb118f7c4fe2c5024/c.html'
url4 = 'http://www.news.cn/politics/xxjxs/index.htm'

def concurrent_contents_qa(contents):
    llms = Concurrent_LLMs(in_url=in_api_url)
    num = len(contents)
    llms.init(
        in_max_new_tokens=in_max_new_tokens,
        in_prompts=[in_prompt]*num,
        in_contents=in_contents,
        in_content_short_enough=in_content_short_enough,
        # in_stream_buf_callbacks=None,
    )
    status = llms.start_and_get_status()
    results = llms.wait_all(status)
    summaries = results['llms_full_responses']

if __name__ == '__main__':
    url1='https://mp.weixin.qq.com/s/DFIwiKvnhERzI-QdQcZvtQ'
    # url='https://segmentfault.com/a/1190000044298001'
    # url='https://www.jianshu.com/p/01c905aaf661'
    # url='https://www.reddit.com/r/QualityAssurance/comments/145mskt/page_object_model_on_playwright/'   # reddit，必须用其api
    # url='https://baijiahao.baidu.com/s?id=1803695466127542316'
    # url='https://zhuanlan.zhihu.com/p/135953477'    # 正文乱码
    # url='https://zhuanlan.zhihu.com/p/379049774'    # 正文乱码
    # url='https://ubuntu.letout.cn/guide/prepare/native.html'

    # url='https://zh.wikihow.com/%E5%AE%89%E8%A3%85Ubuntu-Linux'
    url2='https://blog.csdn.net/qq_45058208/article/details/137617049'
    url3='https://www.zhihu.com/zvideo/1503506180123537408?utm_id=0'    # 知乎带视频（解析不出来）
    url4='https://www.jianshu.com/p/748435a16acc'    # 简书（解析ok）
    url5='https://zhuanlan.zhihu.com/p/534134247'    # 知乎专栏
    url6='https://zhuanlan.zhihu.com/python-programming'    # 知乎专栏
    # url='https://blog.csdn.net/Python_0011/article/details/131633534'

    # print(f'{quick_get_url_text(url, use_proxy=False)}')
    # print(f'{quick_get_url_text(url, use_proxy=False)}')

    # ===获取bing搜索结果===
    result_url_list = get_bing_search_result(query='万向创新聚能城', result_num=20, show_results_in_one_page=50, use_proxy=False)
    for i, item in enumerate(result_url_list):
        print(f"{i+1:>2d}) {item}")

    # ===获取bing搜索结果对应url的所有content===
    # url_list = get_bing_search_result(query='万向创新聚能城', result_num=1, show_results_in_one_page=20, use_proxy=False)
    # print(url_list)
    # content_list = get_urls_content_list(url_list, res_type_list=['video', 'image', 'text'], use_proxy=False)
    # for url in (url_list):
    #     print(f'================================={url}==========================================')
    #     for item in content_list[url]:
    #         print(item)

    # ===获取多个urls下的content的list===
    # res = get_urls_content_list([url1, url2], res_type_list=['video', 'image', 'text'], use_proxy=False)
    # for item in res[url1]:
    #     print(item)
    # for item in res[url2]:
    #     print(item)

    # ===获取一个url下的content的list===
    # res = get_url_content_list(url6, res_type_list=['video', 'image', 'text'], use_proxy=False)
    # for item in res:
    #     print(item)

    # ===获取多个urls的文本===
    # dict = get_urls_text([url1, url2])
    # print(dict[url1])
    # print(dict[url2])

    # ===获取一个url的文本===
    # url = url1
    # url = 'https://so.toutiao.com/search?dvpf=pc&source=input&keyword=%E4%BB%8A%E6%97%A5%E7%83%AD%E7%82%B9'
    # txt = get_url_text(url)
    # print(txt)

    # 测试，如头条、热点等入口网站的urls获取
    # loop = asyncio.new_event_loop()
    # loop.run_until_complete(try_to_get_urls_of_some_search_site(url='https://www.baidu.com/s?ie=utf-8&f=3&rsv_bp=1&rsv_idx=1&tn=baidu&wd=foo'))
    # # loop.run_until_complete(try_to_get_urls_of_some_search_site(url='https://www.toutiao.com'))
    # while(True):
    #     time.sleep(1)
