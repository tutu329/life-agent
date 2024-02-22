from playwright.async_api import async_playwright
from typing import List, Dict, Tuple, Optional
import json
import re
import asyncio

from tools.retriever.html2text import html2text
from utils.print_tools import print_long_content_with_urls, get_string_of_long_content_with_urls
from utils.long_content_summary import long_content_qa, long_content_qa_concurrently, long_content_qa_concurrently_yield
from utils.task import Flicker_Task

SEARCH_TIME_OUT = 3000    # 超时ms

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
    def __init__(self,
                 in_search_num=3,
                 in_llm_api_url='http://127.0.0.1:8001/v1',
                 in_stream_buf_callback=None,
                 ):
        self.loop = None    # searcher实例对应的loop(主要用于win下streamlit等特定场景)
        self.browser = None
        self.context = None
        self.results = {}
        self.llm_api_url = in_llm_api_url

        self.search_num = in_search_num

        self.flicker = None # 闪烁的光标
        self.stream_buf_callback = in_stream_buf_callback

    # fix_streamlit_windows_proactor_eventloop_problem()必须在任何async调用之前运行
    @staticmethod
    def _fix_streamlit_windows_proactor_eventloop_problem():
        # -------------------------------------解决streamlit调用playwright的async代码的NotImplementedError问题-------------------------------------
        # https://github.com/streamlit/streamlit/issues/7825
        # Playwright requires the Proactor event loop on Windows to run its driver in a subprocess, as the Selector event loop does not support async subprocesses. The Proactor event loop has replaced the Selector event loop as the default event loop on Windows starting with Python 3.8.
        # WindowsProactorEventLoopPolicy(这是目前windows 支持的EventLoop)
        # WindowsSelectorEventLoopPolicy(目前windows不支持这个EventLoop)
        print(f'asyncio.get_event_loop_policy(): {type(asyncio.get_event_loop_policy())}')
        from asyncio import (WindowsProactorEventLoopPolicy, WindowsSelectorEventLoopPolicy)
        asyncio.set_event_loop_policy(WindowsProactorEventLoopPolicy())
        print(f'asyncio.get_event_loop_policy(): {type(asyncio.get_event_loop_policy())}')
        # -------------------------------------- -----------------------------------------------------------------------------------------------

    def search(self, in_question):
        try:
            async def _search(in_question):
                return await self._query_bing_and_get_results(in_question)

            res = self.loop.run_until_complete(_search(in_question))
        except Exception as e:
            print(f'search()异常: "{e}"')
            return None
        return res

    # 【legacy】并发的联网搜索和并发的llm解读，返回最终回复对应的llm对象和搜索urls清单
    def legacy_search_and_ask(self, in_question):
        prompt = in_question
        self.flicker = Flicker_Task(in_stream_buf_callback=self.stream_buf_callback)
        self.flicker.init(in_streamlit=True).start()

        internet_search_resultes = self.search(prompt)  # [(url, content_para_list), (url, content_para_list), ...]
        print_long_content_with_urls(internet_search_resultes)

        contents = []
        search_urls = []
        for result in internet_search_resultes:
            web_url = result[0]
            search_urls.append(web_url)
            content_list = result[1]
            contents.append('\n'.join(content_list))
        llm = long_content_qa_concurrently(in_contents=contents, in_prompt=prompt, in_api_url=self.llm_api_url, in_search_urls=search_urls)
        self.flicker.set_stop()
        return llm, search_urls

    # 并发的联网搜索和并发的llm解读，返回最终回复对应的llm对象和搜索urls清单
    def search_and_ask_yield(self, in_question, in_max_new_tokens=2048,):
        prompt = in_question

        internet_search_resultes = self.search(prompt)  # [(url, content_para_list), (url, content_para_list), ...]

        yield get_string_of_long_content_with_urls(internet_search_resultes) + '\n\n'

        contents = []
        search_urls = []
        gen = None
        if internet_search_resultes is not None:
            for result in internet_search_resultes:
                web_url = result[0]
                search_urls.append(web_url)
                content_list = result[1]
                contents.append('\n\n'.join(content_list))

            gen = long_content_qa_concurrently_yield(
                in_contents=contents,
                in_prompt=prompt,
                in_api_url=self.llm_api_url,
                in_search_urls=search_urls,
                in_max_new_tokens=in_max_new_tokens,
            )

        if gen is not None:
            for result in gen:
                yield result
            yield '\n\n'
            i=0
            for url in search_urls:
                i+=1
                yield f'[{i}]' + url + '\n\n'
        else:
            yield '网络异常，请重试.\n\n'

    # 初始化并返回searcher实例、返回loop，并对win下streamlit的eventloop进行fix
    @staticmethod
    def create_searcher_and_loop(
            fix_streamlit_in_win=False,
            in_search_num=3,
            in_llm_api_url='http://127.0.0.1:8001/v1',
            in_stream_buf_callback = None,
    ):
        if fix_streamlit_in_win:
            Bing_Searcher._fix_streamlit_windows_proactor_eventloop_problem()

        searcher = Bing_Searcher(
            in_search_num=in_search_num,
            in_llm_api_url=in_llm_api_url,
            in_stream_buf_callback=in_stream_buf_callback,
        )

        async def _searcher_start():
            await searcher._start()

        loop = asyncio.new_event_loop()
        loop.run_until_complete(_searcher_start())
        searcher.loop = loop    # 返回loop，主要是为了在searcher完成start后，在同一个loop中执行query_bing_and_get_results()
        return searcher

    async def _start(self):
        print('启动chrome: await async_playwright().start()')

        p = await async_playwright().start()
        # p = sync_playwright().start()
        print('启动chrome: await p.chromium.launch(channel="chrome", headless=True)')
        self.browser = await p.chromium.launch(channel="chrome", headless=True)   # 启动chrome
        print('启动chrome完毕.')
        self.context = await self.browser.new_context()

    async def __aenter__(self):
        print(f'Bing_Searcher.__enter__() invoked.')
        await self._start()
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

    async def _get_bing_search_raw_page(self, question: str, show_results_in_one_page=50):
        results = []
        # context = self.browser.new_context()
        # print('--------------------------3.1.1-----------------------------')
        page = await self.context.new_page()
        # print('--------------------------3.1.10-----------------------------')
        try:
            await page.goto(f"https://www.bing.com/search?q={question}&count={show_results_in_one_page}")
            # print('--------------------------3.1.2-----------------------------')
        except:
            await page.goto(f"https://www.bing.com")
            await page.fill('input[name="q"]', question)
            await page.press('input[name="q"]', 'Enter')
        try:
            await page.wait_for_load_state('networkidle', timeout=SEARCH_TIME_OUT)
            # print('--------------------------3.1.3-----------------------------')
        except:
            pass
        # page.wait_for_load_state('networkidle')
        search_results = await page.query_selector_all('.b_algo h2')
        # print('--------------------------3.1.4-----------------------------')
        i = 0
        for result in search_results:
            i += 1
            if i > self.search_num*3:    # 很多网页搜索结果为空，因此需要增加搜索空间
                break
                
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
        # print('--------------------------3.1.5-----------------------------')
        return results

    async def _query_bing(self, question, max_tries=3):
        cnt = 0
        while cnt < max_tries:
            cnt += 1
            results = await self._get_bing_search_raw_page(question)
            if results:
                return results

        print('No Bing Result')
        return None

    # 通过bing搜索，并返回结果
    async def _query_bing_and_get_results(self, in_question, max_tries=3):
        # print('--------------------------3-----------------------------')
        res = await self._query_bing(in_question, max_tries=max_tries)
        # print('--------------------------3.1-----------------------------')
        search_result_urls = [result['url'] for result in res]
        search_results = await self._get_raw_pages(search_result_urls)

        results = []
        num = 0
        # print('--------------------------4-----------------------------')
        for k,v in search_results.items():
            # ------每一个url对应的搜索结果------
            url = k
            response_status = v[0]
            response_text = v[1]
            content_para_list = self._html_2_text_paras(response_text)

            if response_status == 200:
                if ''.join(content_para_list) != '' :
                    # 如果content_para_list内容不为空，才添加到结果
                    results.append((url, content_para_list))
                    num += 1

                if num >= self.search_num:
                    break

        # print('--------------------------5-----------------------------')
        return results  # [(url, content_para_list), (url, content_para_list), ...]

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

    async def _get_raw_pages(self, urls):
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
            response = await context.request.get(url, timeout=SEARCH_TIME_OUT)
            # 等待子页面加载完毕
            self.results[url] = (response.status, await response.text())
        except Exception as e:
            print(f'func_get_one_page(url={url}) error: {e}')
            self.results[url] = (response.status, '')
            # self.results[url] = (404, None)   # (response_status, response_html_text)

# search的生成器（必须进行同步化改造，否则progress.tqdm(search_gen(message), desc='正在调用搜索引擎中...')报错！）
def simple_search_gen(in_question):
    async def async_search():
        async with Bing_Searcher() as searcher:
            results = await searcher._query_bing_and_get_results(in_question)
            return results

    yield '搜索引擎开始初始化...'
    loop = asyncio.new_event_loop()
    results = loop.run_until_complete(async_search())
    yield results

# search的最终的同步调用
def simple_search(in_question):
    async def search():
        question = in_question
        async with Bing_Searcher() as searcher:
            results = await searcher._query_bing_and_get_results(question)
            return results

    if __name__ == '__main__':
        loop = asyncio.get_event_loop()     # 本文件main()调用search()，必须用这一行
    else:
        loop = asyncio.new_event_loop()     # gradio调用search()，必须用这一行
    res = loop.run_until_complete(search())
    return res

def main():
    from tools.llm.api_client import LLM_Client

    question = '杭州有哪些著名景点'

    llm = LLM_Client(history=False, url='http://127.0.0.1:8002/v1')

    res = simple_search(question)
    print(f'====================开始搜索，question: {question}, res: {res}====================')
    for url, content_para_list in res:
        print(f'====================url: {url}====================')
        content = " ".join(content_para_list)
        print(f'====================返回文本(总长:{len(content)}): {content_para_list}====================')

        if len(content)<5000:
            prompt = f'这是网络搜索结果: "{content}", 请根据该搜索结果用中文回答用户的提问: "{question}"。'
            llm.ask_prepare(prompt).get_answer_and_sync_print()

def main_linux():
    # prompt = '杭州有哪些著名景点'
    prompt = '李白是谁？'
    print(f'prompt: {prompt}')
    searcher = Bing_Searcher.create_searcher_and_loop(fix_streamlit_in_win=False, in_search_num=3)
    internet_search_resultes = searcher.search(prompt)
    print(f'internet_search_result: {internet_search_resultes}')

def main_search_and_summery(question='李白和杜甫关系如何'):
    searcher = Bing_Searcher.create_searcher_and_loop(fix_streamlit_in_win=False, in_search_num=5, in_llm_api_url='http://127.0.0.1:8001/v1')
    llm, urls = searcher.legacy_search_and_ask(question)
    llm.get_answer_and_sync_print()
    # searcher.search_and_ask('2024年有什么大新闻？')

def main_search_and_summery_yield(question='李白和杜甫关系如何'):
    searcher = Bing_Searcher.create_searcher_and_loop(fix_streamlit_in_win=False, in_search_num=3, in_llm_api_url='http://127.0.0.1:8001/v1')
    gen = searcher.search_and_ask_yield(question, in_max_new_tokens=1024)
    for result in gen:
        print(result, end='', flush=True)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--q", help="question")
    args = parser.parse_args()

    main_search_and_summery_yield(args.q)
