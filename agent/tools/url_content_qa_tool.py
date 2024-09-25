from agent.base_tool import Base_Tool
from utils.extract import extract_dict_string
from utils.folder import get_folder_files_info_string
import json5

from config import dred, dgreen, dblue
from tools.llm.api_client import LLM_Client
from tools.retriever.legacy_search import Bing_Searcher
from tools.qa.long_content_qa import long_content_qa_concurrently

class Url_Content_QA_Tool(Base_Tool):
    name='QA_Url_Content_Tool'
    description='通过提供url就能获取网页内容并对其进行QA问答的工具.'
    parameters=[
        {
            'name': 'url',
            'type': 'string',
            'description': '网页的url地址',
            'required': 'True',
        },
        {
            'name': 'question',
            'type': 'string',
            'description': '对网页的问题',
            'required': 'True',
        },
    ]
    def __init__(self):
        pass

    def call(self, in_thoughts):
        dict_string = extract_dict_string(in_thoughts)
        dict = json5.loads(dict_string)
        url = dict['tool_parameters']['url']
        question = dict['tool_parameters']['question']
        print(f'QA_Url_Content_Tool.call(): dict obj is: {dict}')
        print(f'QA_Url_Content_Tool.call(): url is: "{url}"')
        print(f'QA_Url_Content_Tool.call(): question is: "{question}"')

        llm = LLM_Client(history=False, max_new_tokens=1024, print_input=False, temperature=0, url=config.Domain.llm_url)

        searcher = Bing_Searcher.create_searcher_and_loop()
        result = searcher.loop.run_until_complete(searcher.get_url_content(in_url=url))


        # gen = long_content_qa(in_llm=llm, in_content=result, in_prompt=question)
        gen = long_content_qa_concurrently(in_llm=llm, in_content=result, in_prompt=question)
        action_result = ''
        for chunk in gen:
            print(chunk, end='', flush=True)
            action_result += chunk
        return action_result
