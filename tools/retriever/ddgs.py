# pip install -U duckduckgo_search

import asyncio
from duckduckgo_search import AsyncDDGS
from duckduckgo_search import DDGS

from config import Global,dred,dblue,dgreen
import json

async def one_query_results(in_query):
    try:
        results = await AsyncDDGS(
            proxies=Global.ddgs_proxies
        ).text(
            in_query,
            region='us-en',     # region: wt-wt, us-en, uk-en, ru-ru, etc. Defaults to "wt-wt".
            timelimit='m',      # timelimit: d, w, m, y. Defaults to None.
            safesearch='off',
            max_results=Global.ddgs_search_max_num,
            backend='api',
            # backend='html',
            # backend='lite',
        )
    except Exception as e:
        dred(f'ddgs.one_query_results error: "{e}"')
        return []

    return results

async def multi_queries_results(in_query_list):
    try:
        tasks = [one_query_results(w) for w in in_query_list]
        results = await asyncio.gather(*tasks)
    except Exception as e:
        dred(f'ddgs.multi_queries_results error: "{e}"')
        return []
    # results: [
    #   {
    #     'title': ...
    #     'href': ...
    #     'body': ...
    #   },
    # ]
    return results

async def async_main():
    queries = ["how to use playwright to get the content of reddit.com"]
    # queries = ["sun", "earth", "moon"]
    results = await multi_queries_results(queries)

    i=0
    for w in queries:
        for text in results[i]:
            dred(text['title'])
            dgreen(text['href'])
            print(text['body'])
        i += 1

def sync_main():
    # 执行文本搜索
    results = DDGS(
        proxies=Global.ddgs_proxies
    ).text('duckduckgo_search的proxies怎么填写', max_results=5)
    # results = DDGS(proxies=Global.ddgs_proxies).text('python programming', max_results=5)
    for text in results:
        dred(text['title'])
        print(text['href'])
        print(text['body'])

if __name__ == "__main__":
    asyncio.run(async_main())
    # sync_main()