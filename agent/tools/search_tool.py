from agent.tools.base_tool import Base_Tool
from utils.extract import legacy_extract_dict_string
import json5

from tools.retriever.search_and_urls import concurrent_search_and_summary_with_final_qa_gen
from tools.retriever.legacy_search import Bing_Searcher

class Search_Tool(Base_Tool):
    name='Search_Tool'
    description='通过搜索引擎对query进行搜索，并根据prompt将搜索结果总结为摘要后返回的工具.'
    parameters=[
        {
            'name': 'query',
            'type': 'string',
            'description': '搜索的关键词',
            'required': 'True',
        },
        {
            'name': 'prompt',
            'type': 'string',
            'description': '根据搜索结果向大语言模型提问的提示词',
            'required': 'True',
        },
    ]
    def __init__(self):
        self.searcher = None

    # 初始化searcher
    def init(self):
        searcher = Bing_Searcher.create_searcher_and_loop(in_search_num=3)

    def call(self, in_thoughts):
        dict_string = legacy_extract_dict_string(in_thoughts)

        # print(Fore.RED, flush=True)
        # print('-----------Search_Tool: dict string to get tool_name is:----------')
        # print(dict_string)
        # print('------------------------------------------------------------------')
        # print(Style.RESET_ALL, flush=True)
        dict = json5.loads(dict_string)
        query = dict['tool_parameters']['query']
        prompt = dict['tool_parameters']['prompt']
        print(f'Search_Tool.call(): dict obj is: {dict}')
        print(f'Search_Tool.call(): query is: "{query}"')
        print(f'Search_Tool.call(): prompt is: "{prompt}"')

        # searcher = Bing_Searcher.create_searcher_and_loop(in_search_num=3)
        # gen = searcher.search_and_ask_yield(query, in_max_new_tokens=1024)

        gen = concurrent_search_and_summary_with_final_qa_gen(
            prompt=prompt,
            # prompt='请根据所提供材料，总结万向创新聚能城的概况',
            search_keywords_string=query,
            search_result_num=5,
            # search_keywords_string='万向创新聚能城',
        )

        action_result = ''
        for chunk in gen:
            action_result += chunk

        # summaries_string = concurrent_search_and_summary_without_final_qa(
        #     prompt=prompt,
        #     search_keywords_string=query,
        #     search_result_num=5,
        # )
        #
        # action_result = summaries_string

        return action_result
