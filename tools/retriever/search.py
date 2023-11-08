from playwright.sync_api import sync_playwright
from typing import List, Dict, Tuple, Optional
import json
import asyncio

from tools.retriever.fetch import *

class SearchResult:
    def __init__(self, title, url, snip) -> None:
        self.title = title
        self.url = url
        self.snip = snip

    def dump(self):
        return {
            "title": self.title,
            "url": self.url,
            "snip": self.snip
        }

    def __str__(self) -> str:
        return json.dumps(self.dump())

class Bing_Searcher():
    def __init__(self):
        self.browser = None
        self.context = None

    async def start(self):
        p = await async_playwright().start()
        # p = sync_playwright().start()
        self.browser = await p.chromium.launch(channel="chrome", headless=False)   # 启动chrome
        self.context = await self.browser.new_context()

    # def __del__(self):
    #     if self.browser:
    #         self.browser.close()

    async def get_bing_search_raw_page(self, question: str):
        results = []
        # context = self.browser.new_context()
        page = await self.context.new_page()
        try:
            await page.goto(f"https://www.bing.com/search?q={question}")
        except:
            await page.goto(f"https://www.bing.com")
            await page.fill('input[name="q"]', question)
            await page.press('input[name="q"]', 'Enter')
        try:
            await page.wait_for_load_state('networkidle', timeout=3000)
        except:
            pass
        # page.wait_for_load_state('networkidle')
        search_results = await page.query_selector_all('.b_algo h2')
        for result in search_results:
            title = await result.inner_text()
            a_tag = await result.query_selector('a')
            if not a_tag: continue
            url = await a_tag.get_attribute('href')
            if not url: continue
            # print(title, url)
            results.append({
                'title': title,
                'url': url
            })
        return results

    async def query_bing(self, question, max_tries=3):
        cnt = 0
        while cnt < max_tries:
            cnt += 1
            results = await self.get_bing_search_raw_page(question)
            if results:
                return results
        print('No Bing Result')
        return None

async def main():
    s = Bing_Searcher()
    await s.start()
    res = await s.query_bing('how to cook a cake?')
    print(json.dumps(res, ensure_ascii=False, indent=4))
    urls = [result['url'] for result in res]
    print(f'====================urls: {urls}====================')
    # rtn = get_raw_pages(urls)
    # print(rtn)

    # with open('crawl.json', 'w', encoding='utf-8') as f:
    #     json.dump(query_bing('how to cook a steak'), f, ensure_ascii=False, indent=4)

    # exit(0)


if __name__ == '__main__':
    # loop = asyncio.new_event_loop() # 这个会报io的错
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())