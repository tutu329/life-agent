import json5 as json
import asyncio
import re
from typing import List

from playwright.async_api import async_playwright   # playwright install
from bs4 import BeautifulSoup                       # pip install playwright beautifulsoup4 lxml

from config import dred, dgreen, dblue, Global
from tools.retriever.html2text import html2text

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
                    proxy=Global.playwright_proxy
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
    async def _get_url_content(self, url):


        dgreen(f'获取网页"{url}"的内容...')
        response = None

        try:
            self.results[url] = [None, None]

            response = await self.context.request.get(
                url,
                timeout=Global.playwright_get_url_content_time_out,
            )

            html_content = await response.text()
            title, text = self._html_to_text(html_content)

            self.results[url] = {
                'status': response.status,
                'html_content': html_content,
                'text': text,
                'title': title,
            }

        except Exception as e:
            dred(f'_get_url_content() error: {e}')
            if response is not None:
                self.results[url] = (response.status, '')
            else:
                self.results[url] = (404, '获取网页内容失败.')

    def _html_to_text(self, html):
        # 使用 BeautifulSoup 解析 HTML 并提取正文
        soup = BeautifulSoup(html, 'html.parser')

        title_tag = soup.find('title')
        title = title_tag.get_text() if title_tag else ''
        title = title.strip()

        # 提取正文内容
        # 你可以根据实际情况调整选择器
        body = soup.find('body')  # 获取页面的 <body> 内容
        paragraphs = body.find_all('p') if body else []  # 获取所有 <p> 标签内容

        # 将所有段落的文本合并成一个字符串
        text_content = '\n'.join([p.get_text() for p in paragraphs])

        return title, text_content

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
    url = 'https://mp.weixin.qq.com/s/DFIwiKvnhERzI-QdQcZvtQ'
    # url = 'http://www.news.cn/politics/leaders/20240703/3f5d23b63d2d4cc88197d409bfe57fec/c.html'

    async with Urls_Content_Retriever() as r:
        await r._get_url_content(url)
        print(f'title: "{r.results[url]["title"]}"')
        print(f'text: "{r.results[url]["text"]}"')
        # print(r.results[url]['html_content'])

if __name__ == '__main__':
    asyncio.run(main())