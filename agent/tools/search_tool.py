from agent.base_tool import Base_Tool
from utils.extract import extract_dict_string
from utils.folder import get_folder_files_info_string
import json5

from config import dred, dgreen, dblue
from tools.retriever.legacy_search import Bing_Searcher

class Search_Tool(Base_Tool):
    name='Search_Tool'
    description='通过bing搜索引擎对query进行搜索，并返回搜索结果的工具.'
    parameters=[
        {
            'name': 'query',
            'type': 'string',
            'description': '搜索的关键词',
            'required': 'True',
        },
    ]
    def __init__(self):
        self.searcher = None

    # 初始化searcher
    def init(self):
        searcher = Bing_Searcher.create_searcher_and_loop(in_search_num=3)

    def call(self, in_thoughts):
        dict_string = extract_dict_string(in_thoughts)

        # print(Fore.RED, flush=True)
        # print('-----------Search_Tool: dict string to get tool_name is:----------')
        # print(dict_string)
        # print('------------------------------------------------------------------')
        # print(Style.RESET_ALL, flush=True)
        dict = json5.loads(dict_string)
        query = dict['tool_parameters']['query']
        print(f'Search_Tool.call(): dict obj is: {dict}')
        print(f'Search_Tool.call(): query is: "{query}"')

        searcher = Bing_Searcher.create_searcher_and_loop(in_search_num=3)
        gen = searcher.search_and_ask_yield(query, in_max_new_tokens=1024)
        action_result = ''
        for res in gen:
            chunk = res['response']
            if res['response_type']=='final':
                print(chunk, end='', flush=True)
                action_result += chunk
        return action_result
