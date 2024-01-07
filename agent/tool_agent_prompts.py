from typing import Dict, List, Union

PROMPT_REACT = """Answer the following questions as best you can. You have access to the following tools:

{tool_descs}Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can be repeated zero or more times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {query}"""

class Base_Tool():
    name: str
    description: str
    parameters: List[Dict]

    def __init__(self):
        pass

class Search_Tool(Base_Tool):
    name='search_tool'
    description='通过bing进行网页搜索的工具'
    parameters=[
        {
            'name': 'query',
            'type': 'string',
            'description': '搜索的关键词',
            'required': 'True',
        },
    ]
    def __init__(self):
        pass

class Code_Tool(Base_Tool):
    name='code_tool'
    description='通过python进行编程的工具'
    parameters=[
        {
            'name': 'code',
            'type': 'string',
            'description': 'python代码',
            'required': 'True',
        },
    ]
    def __init__(self):
        pass
