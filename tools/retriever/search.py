from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright

from typing import List
import json
import re
import asyncio
from colorama import Fore, Style

from tools.retriever.html2text import html2text
from utils.print_tools import print_long_content_with_urls, get_string_of_long_content_with_urls
from tools.qa.long_content_qa import multi_contents_qa_concurrently, multi_contents_qa_concurrently_yield
from utils.task import Flicker_Task

from config import Prompt_Limitation
from config import Global, dred, dgreen, dblue


SEARCH_TIME_OUT = 3000    # 超时ms

def google_search(keywords: str, num_results: int = 50, time="m") -> str:
    search_results = []
    if not keywords:
        return json.dumps(search_results)

    results = ddg(
        keywords,
        max_results=num_results,
        region="us-en",
        safesearch="off",
        time=time,   # d w m y，即一天内、一周内、一月内、一年内
        )
    if not results:
        return json.dumps(search_results)

    for j in results:
        search_results.append(j)

    # results = json.dumps(search_results, ensure_ascii=False, indent=4)
    return search_results

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
    global_searcher = None

    def __init__(self,
                 in_search_num=3,
                 in_llm_api_url='http://127.0.0.1:8001/v1',
                 in_stream_buf_callback=None,
                 in_use_proxy = False,
                 ):
        self.loop = None    # searcher实例对应的loop(主要用于win下streamlit等特定场景)
        self.browser = None
        self.context = None
        self.results = {}
        self.llm_api_url = in_llm_api_url

        self.search_num = in_search_num

        self.flicker = None # 闪烁的光标
        self.stream_buf_callback = in_stream_buf_callback

        self.use_proxy = in_use_proxy   # 使用v2ray代理

    # fix_streamlit_windows_proactor_eventloop_problem()必须在任何async调用之前运行
    @staticmethod
    def _fix_streamlit_windows_proactor_eventloop_problem():
        # -------------------------------------解决streamlit调用playwright的async代码的NotImplementedError问题-------------------------------------
        # https://github.com/streamlit/streamlit/issues/7825
        # Playwright requires the Proactor event loop on Windows to run its driver in a subprocess, as the Selector event loop does not support async subprocesses. The Proactor event loop has replaced the Selector event loop as the default event loop on Windows starting with Python 3.8.
        # WindowsProactorEventLoopPolicy(这是目前windows 支持的EventLoop)
        # WindowsSelectorEventLoopPolicy(目前windows不支持这个EventLoop)
        print(f'asyncio.get_event_loop_policy(): {type(asyncio.get_event_loop_policy())}')
        from asyncio import (WindowsProactorEventLoopPolicy)
        asyncio.set_event_loop_policy(WindowsProactorEventLoopPolicy())
        print(f'asyncio.get_event_loop_policy(): {type(asyncio.get_event_loop_policy())}')
        # -------------------------------------- -----------------------------------------------------------------------------------------------

    #
    def search(self, in_question):
        print(f'Bing_Searcher.search() entered.', flush=True)
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
        llm = multi_contents_qa_concurrently(in_contents=contents, in_prompt=prompt, in_api_url=self.llm_api_url, in_search_urls=search_urls)
        self.flicker.set_stop()
        return llm, search_urls

    async def get_url_content(self, in_url):
        urls = [in_url]
        urls_results = await self._get_raw_pages(urls)

        results = []
        num = 0

        url = in_url
        response_status = urls_results[url][0]
        response_text = urls_results[url][1]
        content_para_list = self._html_2_text_paras(response_text)

        if response_status == 200:
            result = '\n'.join(content_para_list)
            return result
        else:
            return '网页内容获取失败.'

    # Bing_Searcher的主要入口：并发的联网搜索和并发的llm解读，返回最终回复对应的llm对象和搜索urls清单
    def search_and_ask_yield(self, in_question, in_max_new_tokens=2048, in_para_max=Prompt_Limitation.concurrent_para_max_len_in_search):
        print(f'Bing_Searcher.search_and_ask_yield() entered.', flush=True)
        searcher_and_llms_status = {
            'type'                : 'running',
            'canceled'            : False,
            'describe'            : '启动搜索解读任务...',
            'detail'              : f'正在通过bing.com进行搜索...',
            'llms_complete'       : [False]*self.search_num,
            'llms_full_responses' : ['']*self.search_num,
            'response_type'       : 'debug', # debug | final
            'response'            : '',
        }
        yield searcher_and_llms_status

        prompt = in_question

        internet_search_resultes = self.search(prompt)  # [(url, content_para_list), (url, content_para_list), ...]

        searcher_and_llms_status['response_type'] = 'debug'
        searcher_and_llms_status['response'] =  get_string_of_long_content_with_urls(internet_search_resultes) + '\n\n'
        yield searcher_and_llms_status

        contents = []
        search_urls = []
        gen = None
        if internet_search_resultes is not None:
            i = 1
            for result in internet_search_resultes:
                web_url = result[0]
                search_urls.append(web_url)
                content_list = result[1]
                content = '\n\n'.join(content_list)
                stripped_content = content[:in_para_max]
                print(f'in_para_max: {in_para_max}', flush=True)
                print(f'len of content[{i}]: {len(content)}', flush=True)
                print(f'stripped len of content[{i}]: {len(stripped_content)}', flush=True)
                contents.append(stripped_content)
                i += 1

            gen = multi_contents_qa_concurrently_yield(
                in_contents=contents,
                in_prompt=prompt,
                in_api_url=self.llm_api_url,
                in_search_urls=search_urls,
                in_max_new_tokens=in_max_new_tokens,
            )

        if gen is not None:
            for result in gen:
                searcher_and_llms_status['response_type'] = 'final'
                searcher_and_llms_status['response'] = result
                yield searcher_and_llms_status
            searcher_and_llms_status['response_type'] = 'final'
            searcher_and_llms_status['response'] = '\n\n'
            yield searcher_and_llms_status
            i=0
            for url in search_urls:
                i+=1
                searcher_and_llms_status['response_type'] = 'final'
                searcher_and_llms_status['response'] = f'[{i}]' + url + '\n\n'
                yield searcher_and_llms_status
        else:
            searcher_and_llms_status['response_type'] = 'final'
            searcher_and_llms_status['response'] += '网络异常，请重试.\n\n'
            yield searcher_and_llms_status

    # 初始化并返回searcher实例、返回loop，并对win下streamlit的eventloop进行fix
    @staticmethod
    def create_searcher_and_loop(
            fix_streamlit_in_win=False,
            in_search_num=3,
            in_llm_api_url='http://127.0.0.1:8001/v1',
            in_stream_buf_callback = None,
            in_use_proxy = False,
    ):
        if Bing_Searcher.global_searcher is not None:
            # searcher已经启动时，不再进行初始化，但要注意其他状态是否需要重置
            print(f'Bing_Searcher.create_searcher_and_loop() already invoked.')
            Bing_Searcher.global_searcher.results = {}
            Bing_Searcher.global_searcher.llm_api_url = in_llm_api_url
            Bing_Searcher.global_searcher.search_num = in_search_num
            Bing_Searcher.global_searcher.stream_buf_callback = in_stream_buf_callback
            print(f'refresh searcher paras:')
            print(f'global_searcher.results: {Bing_Searcher.global_searcher.results}')
            print(f'global_searcher.llm_api_url: {Bing_Searcher.global_searcher.llm_api_url}')
            print(f'global_searcher.search_num: {Bing_Searcher.global_searcher.search_num}')
            print(f'global_searcher.stream_buf_callback: {Bing_Searcher.global_searcher.stream_buf_callback}')
            return Bing_Searcher.global_searcher

        print(f'Bing_Searcher.create_searcher_and_loop() entered.')
        if fix_streamlit_in_win:
            Bing_Searcher._fix_streamlit_windows_proactor_eventloop_problem()

        searcher = Bing_Searcher(
            in_search_num=in_search_num,
            in_llm_api_url=in_llm_api_url,
            in_stream_buf_callback=in_stream_buf_callback,
            in_use_proxy = in_use_proxy,
        )

        async def _searcher_start():
            await searcher._start()

        loop = asyncio.new_event_loop()
        loop.run_until_complete(_searcher_start())
        searcher.loop = loop    # 返回loop，主要是为了在searcher完成start后，在同一个loop中执行query_bing_and_get_results()

        Bing_Searcher.global_searcher = searcher
        return searcher

    async def _start(self):
        print('启动chrome: await async_playwright().start()')

        p = await async_playwright().start()
        # p = sync_playwright().start()
        print('启动chrome: await p.chromium.launch(channel="chrome", headless=True)')

        # 启动浏览器
        if self.use_proxy:
            dred(f'启动代理: {Global.playwright_proxy}')

            self.browser = await p.chromium.launch(
                channel="chrome",
                headless=True,
                proxy=Global.playwright_proxy
            )   # 启动chrome
        else:
            dred('未启动代理')

            self.browser = await p.chromium.launch(
                channel="chrome",
                headless=True
            )   # 启动chrome

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
            url = f"https://www.bing.com/search?q={question}&count={show_results_in_one_page}"
            dred(f'page.goto("{url}")')
            await page.goto(url)
            # print('--------------------------3.1.2-----------------------------')
        except Exception as e:
            dred(f'page.goto() error: {e}')
            await page.goto(f"https://www.bing.com")
            await page.fill('input[name="q"]', question)
            await page.press('input[name="q"]', 'Enter')
        try:
            # await page.wait_for_load_state('networkidle')
            await page.wait_for_load_state('networkidle', timeout=SEARCH_TIME_OUT)
            # print('--------------------------3.1.3-----------------------------')
        except:
            pass
        # page.wait_for_load_state('networkidle')
        search_results = await page.query_selector_all('.b_algo h2')
        # dred(f'search_results: {search_results}')
        # print('--------------------------3.1.4-----------------------------')
        i = 0
        for result in search_results:
            i += 1
            # if i > self.search_num*3:    # 很多网页搜索结果为空，因此需要增加搜索空间
            #     dred(f'空页面超过{i-1}个，退出.')
            #     break
                
            title = await result.inner_text()
            a_tag = await result.query_selector('a')
            if not a_tag: continue
            url = await a_tag.get_attribute('href')
            if not url: continue
            # print(title, url)

            dgreen(f'url: "{url}"')

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

        dred('bing.com搜索结果为空.')
        return None

    # 通过bing搜索，并返回结果
    async def _query_bing_and_get_results(self, in_question, max_tries=3):
        # print('--------------------------3-----------------------------')
        res = await self._query_bing(in_question, max_tries=max_tries)
        # print('--------------------------3.1-----------------------------')
        if res is None:
            return []

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

        await asyncio.wait(tasks, timeout=100)

        return self.results

    async def _func_get_one_page(self, context, url):
        # dred(f'get_page: url({url})')
        # 开启事件监听
        # page.on('response',printdata)
        # 进入子页面
        response = None

        # page = await self.context.new_page()
        try:
            self.results[url] = [None, None]

            # response = await page.request.get(
            response = await context.request.get(
                url,
                timeout=SEARCH_TIME_OUT,
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

def main_only_search(args):
    in_query = args.q

    dred(f'query: "{in_query}"')

    searcher = Bing_Searcher.create_searcher_and_loop(fix_streamlit_in_win=False, in_search_num=10, in_use_proxy=True)
    internet_search_resultes = searcher.search(in_query)

    # [(url, content_para_list), (url, content_para_list), ...]
    if internet_search_resultes is None:
        dred('查询结果为空.')
        return

    print(Fore.GREEN, flush=True)
    for res in internet_search_resultes:
        content = ''.join(res[1])
        url = res[0]
        dgreen(f'内容: "{content[:1500]}..."')
        dblue(f'\t\turl: "{url}"')
    print(Style.RESET_ALL, flush=True)

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

def main_test_proxy():

    def search_on_bing(query):
        with sync_playwright() as p:
            browser = p.chromium.launch(
                channel="chrome",
                headless=True,
                proxy=Global.playwright_proxy
            )
            dred('-----1-------')
            context = browser.new_context()

            page = context.new_page()

            url = f"https://www.bing.com/search?q={query}&count={50}"
            dblue(f'page.goto("{url}")')
            page.goto(url)

            # 等待搜索结果加载
            page.wait_for_load_state('load')

            # 获取搜索结果
            search_results = page.query_selector_all('.b_algo h2')

            url_list = []
            for result in search_results:
                a_tag = result.query_selector('a')
                if a_tag:
                    url = a_tag.get_attribute('href')
                    if url:
                        dgreen(f'url: "{url}"')
                        url_list.append(url)
                # print(result.text_content())

            try:
                for url in url_list:
                    dred(f'{"-" * 80}')
                    dblue(f'url: "{url}"')
                    response = context.request.get(url, timeout=3000)
                    # response = requests.get(url)
                    text = response.text()
                    # text = ' '.join(text.split('\n'))
                    dblue(f'内容: {text}')
            except Exception as e:
                dred(f'context.request.get() error: "{e}"')
            browser.close()

    # search_on_bing('4029 reddit.com')
    search_on_bing('using playwright to get content on bing.com reddit.com')

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--q", help="question")
    parser.add_argument("--proxy", default='true', help="v2ray proxy")
    args = parser.parse_args()
    dred('请执行: --q 搜索内容')

    main_only_search(args)
    # main_test_proxy()
    # main_search_and_summery_yield(args.q)

