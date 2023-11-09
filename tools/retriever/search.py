from playwright.async_api import async_playwright
from typing import List, Dict, Tuple, Optional
import json
import re
import asyncio

from tools.retriever.html2text import html2text

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
    def __init__(self, in_show_result_num=3):
        self.browser = None
        self.context = None
        self.results = {}

        self.show_result_num = in_show_result_num

    async def start(self):
        p = await async_playwright().start()
        # p = sync_playwright().start()
        self.browser = await p.chromium.launch(channel="chrome", headless=False)   # 启动chrome
        self.context = await self.browser.new_context()

    async def __aenter__(self):
        print(f'Bing_Searcher.__enter__() invoked.')
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        print(f'Bing_Searcher.__exit__() invoked.')
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()


    # def __del__(self):
    #     if self.browser:
    #         self.browser.close()

    async def _get_bing_search_raw_page(self, question: str):
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
            results = await self._get_bing_search_raw_page(question)
            if results:
                return results

        print('No Bing Result')
        return None

    # 通过bing搜索，并返回结果
    async def query_bing_and_get_results(self, in_question, max_tries=3):
        res = await self.query_bing(in_question, max_tries=max_tries)
        search_result_urls = [result['url'] for result in res]
        search_results = await self.get_raw_pages(search_result_urls)

        results = []
        num = 0
        for k,v in search_results.items():
            # ------每一个url对应的搜索结果------
            url = k
            response_status = v[0]
            response_text = v[1]
            content_para_list = self.html_2_text_paras(response_text)

            if response_status == 200:
                if num > self.show_result_num:
                    break

                results.append((url, content_para_list))
                num += 1

        return results  # [(url, content_para_list), (url, content_para_list), ...]

    def html_2_text_paras(self, html: str) -> List[str]:
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

    async def get_raw_pages(self, urls):
        # 封装异步任务
        tasks = []
        for url in urls:
            tasks.append(asyncio.create_task(self._func_get_one_page(self.context, url)))

        await asyncio.wait(tasks, timeout=10)

        return self.results

    async def _func_get_one_page(self, context, url):
        # 开启事件监听
        # page.on('response',printdata)
        # 进入子页面
        try:
            self.results[url] = [None, None]
            response = await context.request.get(url, timeout=5000)
            # 等待子页面加载完毕
            self.results[url] = (response.status, await response.text())
        except Exception as e:
            print(f'func_get_one_page(url={url}) error: {e}')

def search_gen(in_question):
    async def search():
        question = in_question
        yield None
        async with Bing_Searcher() as searcher:
            yield None
            results = await searcher.query_bing_and_get_results(question)
            yield results
            # return results

    if __name__ == '__main__':
        loop = asyncio.get_event_loop()     # 本文件main()调用search()，必须用这一行
    else:
        loop = asyncio.new_event_loop()     # gradio调用search()，必须用这一行
    gen = loop.run_until_complete(search())

    return gen
def search(in_question):
    async def search():
        question = in_question
        async with Bing_Searcher() as searcher:
            results = await searcher.query_bing_and_get_results(question)
            return results

    if __name__ == '__main__':
        loop = asyncio.get_event_loop()     # 本文件main()调用search()，必须用这一行
    else:
        loop = asyncio.new_event_loop()     # gradio调用search()，必须用这一行
    res = loop.run_until_complete(search())
    return res


from tools.llm.api_client_qwen_openai import *
def main():

    question = '杭州有哪些著名景点'

    llm = LLM_Qwen(history=False)

    res = search(question)
    for url, content_para_list in res:
        print(f'====================url: {url}====================')
        content = " ".join(content_para_list)
        print(f'====================返回文本(总长:{len(content)}): {content_para_list}====================')

        if len(content)<5000:
            prompt = f'这是网络搜索结果: "{content}", 请根据该搜索结果用中文回答用户的提问: "{question}"。'
            llm.ask_prepare(prompt).get_answer_and_sync_print()

if __name__ == '__main__':
    main()
