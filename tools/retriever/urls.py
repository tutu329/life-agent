import json5 as json
import asyncio
import re
from typing import List

from playwright.async_api import async_playwright   # playwright install
from bs4 import BeautifulSoup, Tag                  # pip install playwright beautifulsoup4 lxml

from config import dred, dgreen, dblue, Global
from tools.retriever.legacy_wrong_html2text import html2text
from utils.url import remove_rightmost_path

class Urls_Content_Retriever():
    def __init__(
            self,
            in_use_proxy=False,
    ):
        self.loop = None    # Urls实例对应的loop(主要用于win下streamlit等特定场景)

        self.async_playwright = None
        self.browser = None
        self.context = None

        self.results = {}

        self.use_proxy = in_use_proxy   # 使用v2ray代理

    async def init(self):
        print('启动chrome: await async_playwright().start()')

        p = await async_playwright().start()
        self.async_playwright = p
        # p = sync_playwright().start()
        print('启动chrome: await p.chromium.launch(channel="chrome", headless=True)')

        try:
            # 启动浏览器
            if self.use_proxy:
                dred(f'playwright启动代理: "{Global.playwright_proxy}".')

                self.browser = await p.chromium.launch(
                    channel="chrome",
                    headless=True,
                    proxy=Global.playwright_proxy   # 关于win下报错：A "socket" was not created for HTTP request before 3000ms，查看internet选项的局域网设置中的代理服务器设置，port和该设置一致就行，如shadowsocket是10809而非10808
                )   # 启动chrome

            else:
                dgreen('playwright未启动代理.')

                self.browser = await p.chromium.launch(
                    channel="chrome",
                    headless=True
                )   # 启动chrome

            self.context = await self.browser.new_context()


            print('playwright启动完毕, context已获得.')
        except Exception as e:
            dred(f"Error during browser initialization: {e}")

        return self

    async def __aenter__(self):
        return await self.init()

    async def __aexit__(
            self,
            exc_type,       # The type of the exception (e.g., ValueError, RuntimeError).
            exc_val,        # The exception instance itself.
            exc_tb          # The traceback object. （这三个参数必须写，否则报错：TypeError: Urls_Content_Retriever.__aexit__() takes 1 positional argument but 4 were given）
    ):
        await self.close()

    async def close(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.async_playwright:
            await self.async_playwright.stop()  # 如果没有stop，会报错：ValueError: I/O operation on closed pipe

    async def _get_raw_pages(self, urls):
        # 封装异步任务
        tasks = []
        for url in urls:
            tasks.append(asyncio.create_task(self._get_url_content(self.context, url)))

        await asyncio.wait(tasks, timeout=100)

        return self.results

    def _html_2_text_paras(self, html: str) -> List[str]:
        if html is None:
            return []

        paras = html2text(html).split("\n")
        paras = self._pre_filter(paras)
        return paras

    def _pre_filter(self, paragraphs):
        # sorted_paragraphs = sorted(paragraphs, key=lambda x: len(x))
        # if len(sorted_paragraphs[-1]) < 10:
        #     return []
        ret = []
        for item in paragraphs:
            item = item.strip()
            item = re.sub(r"\[\d+\]", "", item)
            if len(item) < 50:
                continue
            if len(item) > 1200:
                item = item[:1200] + "..."
            ret.append(item)
        return ret

    # 获取url的html内容
    async def _get_url_content(self, url, domain=None):


        dgreen(f'获取网页"{url}"的内容...')
        response = None

        try:
            self.results[url] = [None, None]
            response = await self.context.request.get(
                url,
                # proxies=proxies,
                timeout=Global.playwright_get_url_content_time_out,
            )

            html_content = await response.text()
            # all_text = await self._html_to_text(html_content)
            title, text, text_and_media_list = await self._get_text_and_media(html_content, url, domain=domain)
            # print(f'text_media: {text_media}')

            self.results[url] = {
                'status': response.status,
                'html_content': html_content,
                'title': title,
                # 'text': all_text,
                'text': text,
                'text_and_media_list': text_and_media_list,
            }

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
        paragraphs = body.find_all('p') if body else []  # 获取所有 <p> 标签内容

        # 将所有段落的文本合并成一个字符串
        text_content = '\n'.join([p.get_text() for p in paragraphs])

        return text_content

    async def _get_text_and_media(self, html, url, domain=None) -> list:
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
                # if element.name == 'p' and ([element.children]==[]):       # p为末端节点
                if element.name == 'p' and (not element.find_all('span')) and (not element.find_all('span')):       # p为文本类型的末端节点
                    text = element.get_text().strip() if element.get_text() not in not_needed else ''
                    if text:
                        extracted_content_list.append({'type': 'text-p', 'content':text})
                        extracted_text_list.append(text)
                # elif element.name == 'div' and (not element.find_all('p')) and (not element.find_all('span')):    # div标签下没有p标签的text
                #     text = element.get_text().strip() if element.get_text() not in not_needed else ''
                #     if text and (text not in not_needed):
                #         extracted_content_list.append({'type': 'text-div', 'content':text})
                #         extracted_text_list.append(text)
                elif element.name == 'span' and (not element.find_all('p')) and (not element.find_all('span')):    # span为文本类型的末端节点
                    text = element.get_text().strip() if element.get_text() not in not_needed else ''
                    if text and (text not in not_needed):
                        extracted_content_list.append({'type': 'text-span', 'content':text})
                        extracted_text_list.append(text)
                elif element.name == 'img':
                    # print(f'---------------img element: {element}---------------')
                    # src的图片
                    img_src = element.get('src')
                    if img_src:
                        if not img_src.startswith(('http://', 'https://')): # 如果是相对路径，将其转换为绝对路径
                            img_src = f"{domain}/{img_src.lstrip('/')}"
                        extracted_content_list.append({'type': 'img-src', 'content': img_src})
                    # data-src的图片
                    img_src = element.get('data-src')
                    if img_src:
                        if not img_src.startswith(('http://', 'https://')): # 如果是相对路径，将其转换为绝对路径
                            img_src = f"{remove_rightmost_path(url.rstrip('/'))}/{img_src.lstrip('/')}"
                        extracted_content_list.append({'type': 'img-data-src', 'content': img_src})
                elif element.name == 'video':
                    print(f'---------------video element: {element}---------------')
                    src = element.get('src')
                    if src:
                        if not src.startswith(('http://', 'https://')):  # 如果是相对路径，将其转换为绝对路径
                            src = f"{domain}/{src.lstrip('/')}"
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
                        print(f'---------------video element: {element}---------------')
                        if not src.startswith(('http://', 'https://')):  # 如果是相对路径，将其转换为绝对路径
                            src = f"{domain}/{src.lstrip('/')}"
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
async def main():
    # url = 'https://www.xvideos.com/tags/porn'
    # domain = 'https://www.xvideos.com'
    # url = 'https://www.xvideos.com/video.mdvtou3e47/eroticax_couple_s_porn_young_love'
    # url = 'https://www.xvideos.com/tags/porn'
    url = 'https://cn.nytimes.com/opinion/20230214/have-more-sex-please/'
    # url = 'https://mp.weixin.qq.com/s/DFIwiKvnhERzI-QdQcZvtQ'
    # url = 'http://www.news.cn/politics/leaders/20240703/3f5d23b63d2d4cc88197d409bfe57fec/c.html'
    # url = 'http://www.news.cn/politics/leaders/20240613/a87f6dec116d48bbb118f7c4fe2c5024/c.html'
    # url = 'http://www.news.cn/politics/xxjxs/index.htm'

    # async with Urls_Content_Retriever(in_use_proxy=False) as r:
    async with Urls_Content_Retriever(in_use_proxy=True) as r:
        await r._get_url_content(url)

        data_list = r.results[url]["text_and_media_list"]
        txt = r.results[url]["text"]
        for item in data_list:
            print(item)
        print(txt)


if __name__ == '__main__':
    asyncio.run(main())