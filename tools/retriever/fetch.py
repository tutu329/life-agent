import asyncio
from playwright.async_api import async_playwright, Page

class Url_Content_Fetcher():
    def __init__(self, in_browser):
        self.browswer = in_browser

        self.results = {}
        self.status = {}
        self.context = None

    async def one_page_handle(self, context, url):
        # 开启事件监听
        # page.on('response',printdata)
        # 进入子页面
        try:
            self.results[url] = [None, None]
            response = await context.request.get(url, timeout=5000)
            # 等待子页面加载完毕
            self.results[url] = (response.status, await response.text())
        except Exception as e:
            pass

    async def get_context(self):
        if not self.context:
            # print("加载驱动")
            playwright = await async_playwright().start()
            browser = await playwright.firefox.launch()
            # 新建上下文
            self.context = await browser.new_context()
        return context

    async def close_browser(self, browser):
        # 关闭浏览器驱动
        await browser.close()

    async def get_raw_pages_(self, context, urls):
        # 封装异步任务
        tasks = []
        global results
        results = {}
        for url in urls:
            tasks.append(asyncio.create_task(self.one_page_handle(context, url)))

        await asyncio.wait(tasks, timeout=10)

    async def get_raw_pages(self, urls, close_browser=False):
        context = await self.get_context()
        await self.get_raw_pages_(context, urls)

async def main():
    pass

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())