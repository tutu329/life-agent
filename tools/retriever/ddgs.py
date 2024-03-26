# pip install -U duckduckgo_search

import asyncio
from duckduckgo_search import AsyncDDGS
from duckduckgo_search import DDGS

from config import Global,dred,dblue,dgreen
import json

async def get_results(word):
    results = await AsyncDDGS(
        proxies=Global.ddgs_proxies
    ).text(
        word,
        region='us-en',
        safesearch='off',
        max_results=3,
        backend='api',
        # backend='html',
        # backend='lite',
    )
    return results

async def async_main():
    words = ["how to use playwright to get the content of reddit.com"]
    # words = ["sun", "earth", "moon"]
    tasks = [get_results(w) for w in words]
    results = await asyncio.gather(*tasks)

    i=0
    for w in words:
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