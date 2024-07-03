import json5 as json
import asyncio
from playwright.async_api import async_playwright

from config import dred, dgreen, dblue, Global

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

    async def _get_url_content(self, url):
        # dred(f'get_page: url({url})')
        # 开启事件监听
        # page.on('response',printdata)
        # 进入子页面
        response = None

        # page = await self.context.new_page()
        try:
            self.results[url] = [None, None]

            # response = await page.request.get(
            response = await self.context.request.get(
                url,
                timeout=Global.playwright_get_url_content_time_out,
            )
            # 等待子页面加载完毕
            self.results[url] = (response.status, await response.text())
            # dred(f'{"-"*80}')
            # dblue( self.results[url][1])
        except Exception as e:
            dred(f'func_get_one_page(url={url}) error: {e}')
            if response is not None:
                self.results[url] = (response.status, '')
            else:
                self.results[url] = (404, '获取网页内容失败.')

async def main():
    import time
    async with Urls_Content_Retriever() as r:
        await r._get_url_content('http://www.news.cn/politics/leaders/20240703/3f5d23b63d2d4cc88197d409bfe57fec/c.html')
        print(r.results)

if __name__ == '__main__':
    asyncio.run(main())