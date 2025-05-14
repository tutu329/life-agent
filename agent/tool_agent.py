# pip install pyinstaller
# -----------用pyinstaller生成可执行代码-----------
# 在/home/tutu/server/life-agent下：
# 正常运行代码是：
# python -m agent.tool_agent
# 转换代码是：
# pyinstaller agent/tool_agent.py --paths=. --distpath ~/
# 其中“--paths=.”表示将/home/tutu/server/life-agent加入到PyInstaller分析路径中，以便找到tools模块
# 可执行代码将输出至~/tool_agent/下，包括可执行代码和关联so等文件

from tools.llm.api_client import LLM_Client
from agent.base_tool import PROMPT_REACT
from agent.base_tool import Base_Tool

import config
from config import dred, dgreen, dblue, dcyan, dyellow
from server_manager.web_server_base import Web_Server_Base
from agent.agent_config import Config
from utils.extract import extract_dict_string
import json5
from uuid import uuid4

class Tool_Agent(Web_Server_Base):
    def __init__(self,
                 query,
                 tool_classes,
                 agent_config:Config,
                 ):
        self.llm = None
        self.agent_config = agent_config
        self.agent_id = str(uuid4())

        self.temperature = self.agent_config.temperature
        self.url = self.agent_config.base_url
        self.api_key = self.agent_config.api_key
        self.model_id = self.agent_config.model_id
        self.agent_tools_description_and_full_history = ''
        # self.remove_content_in_think_pairs = remove_content_in_think_pairs  # 是否think模型
        self.query=query
        self.tool_descs=''
        self.tool_names=[]

        self.tool_classes = tool_classes
        # 创建一个字典，将工具名称映射到其实例
        self.registered_tool_instances_dict = {}
        for tool_cls in tool_classes:
            tool_instance = tool_cls()
            tool_name = tool_cls.__name__
            self.registered_tool_instances_dict[tool_name] = tool_instance

        # self.human = in_human    # 是否和human交互
        self.action_stop = ['[观察]']
        self.observation_stop = ['[观察]']
        self.response_stop = ['[观察]']
        # self.response_stop = ['<结束>']
        # self.response_stop = ['<res_stop>']
        self.turns_num = 0  # 用于统计当前对象的action轮次

        self.ostream_end_func = self.agent_config.output_end               # 最终结果stream输出的end的func
        self.ostream_use_chunk = self.agent_config.output_stream_use_chunk # 最终结果输出方式：chunk还是full_string
        self.output_stream_to_console = self.agent_config.output_stream_to_console
        self.sstream = self.agent_config.status_stream_buf                 # 中间状态输出的stream

        # self.status_list = inout_status_list     # 状态历史
        self.output_list = self.agent_config.inout_output_list     # 输出历史

        self.__finished_keyword = '最终答复'
        self.final_answer = '尚未进行分析和答复'

    # 设置最终结果stream输出的func
    def set_stream(self, result_output_func, thinking_output_func, log_output_func, tool_result_data_output_func):
        self.agent_config.web_server_stream_result = result_output_func                        # stream输出的func
        self.agent_config.web_server_stream_thinking = thinking_output_func                    # stream输出的func
        self.agent_config.web_server_stream_log = log_output_func                              # stream输出的func
        self.agent_config.web_server_stream_tool_client_data = tool_result_data_output_func    # stream输出的func

    # 最终结果输出
    def output_print(self, in_string):
        if self.output_stream_buf is not None:
            self.output_stream_buf(in_string)

            if self.output_list is not None:
                self.output_list.append(in_string)
        else:
            pass
            # print(in_string)

    # 中间状态输出
    def status_print(self, in_string):
        if self.sstream is not None:
            self.sstream(in_string)

            if self.status_list is not None:
                self.status_list.append(in_string)
        else:
            pass
            # print(in_string)

    # 最终结果stream输出full_string
    def output_result_stream_full_string(self, in_full_response):
        if self.agent_config.web_server_stream_result is not None:
            self.agent_config.web_server_stream_result(in_full_response)

    # 最终结果stream输出chunk，注意：要确保chunk中没有'[最终答复]'或'终答复]'
    def output_result_stream_chunk(self, chunk, **kwargs):
        if self.agent_config.web_server_stream_result is not None:
            self.agent_config.web_server_stream_result(chunk, **kwargs)

    # thinking内容的stream输出chunk
    def output_thinking_stream_chunk(self, chunk, **kwargs):
        if self.agent_config.web_server_stream_thinking is not None:
            self.agent_config.web_server_stream_thinking(chunk, **kwargs)

    # log内容的stream输出chunk
    def output_log_stream_chunk(self, chunk, **kwargs):
        if self.agent_config.web_server_stream_log is not None:
            self.agent_config.web_server_stream_log(chunk, **kwargs)

    # 中间状态stream输出(注意：streamlit的status不支持stream输出，只能打印)
    def output_status_stream(self, in_chunk, in_full_response):
        if self.sstream is not None:
            # self.sstream(in_chunk)
            pass
        else:
            pass
            # print(in_chunk, end='', flush=True)

    def init(self):
        self.llm = LLM_Client(
            url=self.url,
            api_key=self.api_key,
            model_id=self.model_id,
            temperature=self.temperature,
            history=False,
            print_input=False,
            max_new_tokens=config.LLM_Default.max_new_tokens
        )
        self.agent_tools_description_and_full_history = PROMPT_REACT

        # 将所有工具转换为{tool_descs}和{tool_names}
        for tool in self.tool_classes:
            self.tool_names.append(f"'{tool.name}'")
            self.tool_descs += '工具名称: ' + tool.name + '\n'
            self.tool_descs += '工具描述: ' + tool.description + '\n'
            self.tool_descs += '工具参数: [\n'
            for para in tool.parameters:
                self.tool_descs += '\t{'

                self.tool_descs += '\t参数名称: ' + para['name'] + ',\n'
                self.tool_descs += '\t\t参数类型: ' + para['type'] + ',\n'
                self.tool_descs += '\t\t参数描述: ' + para['description'] + ',\n'
                self.tool_descs += '\t\t参数是否必需: ' + para['required'] + ',\n'

                self.tool_descs += '\t},'
            self.tool_descs += '\n]\n\n'

        self.tool_names = ','.join(self.tool_names)

        self.agent_tools_description_and_full_history = self. agent_tools_description_and_full_history.format(tool_descs=self.tool_descs, tool_names=self.tool_names, query=self.query)

    def get_final_answer(self):
        return self.final_answer

    def _parse_final_answer(self, answer):
        # self.__finished_keyword = '最终答复'
        # 去掉'[最终答复]'及之前的内容
        self.final_answer = answer.split(f'[{self.__finished_keyword}]')[-1]
        # print(f'self.final_answer已解析，final answer关键字"{self.__finished_keyword}"已去除.')

    def run(self, in_max_retry=config.Agent.MAX_TRIES):
        dblue(f'config.Agent.MAX_TRIES = {in_max_retry}')
        for i in range(in_max_retry):
            # 1、思考
            answer_this_turn = self.thinking()
            if self.__finished_keyword in answer_this_turn:
                self._parse_final_answer(answer_this_turn)
                return True

            # 2、行动
            action_result = self.action(in_answer=answer_this_turn)
            # 3、观察
            self.observation(in_action_result=action_result)

        self.final_answer = '未能成功答复，请重试。'
        return False

    def _thoughts_stream_output(self, gen):
        thoughts = ''
        thoughts_copy_to_print = ''

        # stream输出
        str_last_turn = ''
        for chunk in gen:
            chunk = chunk[2]

            thoughts +=chunk

            dgreen(chunk, end='', flush=True)
            thoughts_copy_to_print +=chunk
            if f'[{self.__finished_keyword}]' in thoughts:
                # 最终结果stream输出(去除'[最终答复]'这些字)
                if self.ostream_use_chunk:
                    # 采用chunk输出，chunk = string_this_turn - string_last_turn
                    str_this_turn = thoughts.split(f'[{self.__finished_keyword}]')[-1]  # 去除'[最终答复]'这些字
                    # dyellow(f'-----> "{str_this_turn}"')
                    if self.output_stream_to_console:
                        # 输出到console
                        self.output_result_stream_chunk(
                            str_this_turn.split(str_last_turn)[-1] if str_last_turn != '' else str_this_turn ,
                            end='',
                            flush=True
                        )
                    else:
                        # 输出到如word文档中
                        self.output_result_stream_chunk(str_this_turn.split(str_last_turn)[-1] if str_last_turn != '' else str_this_turn)
                        # self.thinking_stream_chunk( str_this_turn.split(str_last_turn)[-1] if str_last_turn != '' else str_this_turn )
                    str_last_turn = str_this_turn
                else:
                    # 采用full_string输出
                    self.output_result_stream_full_string(thoughts.split(f'[{self.__finished_keyword}]')[-1])    # 去除'[最终答复]'这些字
                    # self.output_stream(chunk, thoughts.replace(self.__finished_keyword, ''))
            else:
                self.output_thinking_stream_chunk(chunk)
                # 中间状态stream输出(streamlit的status不支持stream输出，所以这里为空操作，并在后续作status_print处理)
                # self.status_stream(chunk, thoughts)

                # 注意：这里必须是'\n\n'，和agent输出有关，如果是'\n'就会导致页面上额外输出了一行
                if '\n\n' in thoughts_copy_to_print:
                    # 输出已经有\n的内容
                    print_content = thoughts_copy_to_print.split('\n\n')[0]
                    self.status_print(print_content)
                    # if self.status_list is not None:
                    #     self.status_list.append(print_content)
                    # 删除第一个\n前的内容
                    l = thoughts_copy_to_print.split('\n\n')
                    l.pop(0)
                    thoughts_copy_to_print = '\n\n'.join(l)    # 这里用' '.join而不用'\n'.join是为了防止streamlit中status.markdown额外输出\n
        dgreen()

        # stream输出最后的end
        if self.ostream_end_func:
            self.ostream_end_func()

        # 添加输出历史
        if self.__finished_keyword in thoughts:
            # 最终结果输出历史
            if self.output_list is not None:
                self.output_list.append(thoughts.split(f'[{self.__finished_keyword}]')[-1])    # 去除'[最终答复]'这些字
                # self.output_list.append(thoughts.replace(self.__finished_keyword, ''))
        else:
            # 中间状态输出历史
            # self.status_print(thoughts) # streamlit的status无法stream输出，只能这里print输出

            pass
            # if self.status_list is not None:
            #     self.status_list.append(thoughts)

        return thoughts

    def thinking(self):
        self.turns_num += 1
        print(f'thinking(turn {self.turns_num})'.center(80, '='))
        # print(f'原始his: {self.agent_desc_and_action_history}', flush=True)
        dred(f'manual_stop: "{self.response_stop}"')
        gen = self.llm.ask_prepare(
            self.agent_tools_description_and_full_history,
            # stop=self.response_stop,  # vllm的stop（如['观察']）输出有问题，所以暂时作专门处理
            manual_stop = self.response_stop,
        ).get_answer_generator()
        # gen = self.llm.ask_prepare(self.agent_desc_and_action_history, in_stop=self.action_stop).get_answer_generator()
        # thoughts = ''

        answer_this_turn = self._thoughts_stream_output(gen)

        if self.turns_num == 1:
            with open("answer(turn 1).txt", "w", encoding="utf-8") as file:
                file.write(answer_this_turn)

        self.agent_tools_description_and_full_history += '\n' + answer_this_turn

        if self.__finished_keyword in answer_this_turn:
            # '最终答复'出现
            # print(Fore.GREEN, flush=True)
            dblue()
            dblue(f'final answer(turn {self.turns_num})'.center(80, '='))
            dblue(answer_this_turn)
            dblue(f'/final answer(turn {self.turns_num})'.center(80, '-'))

            print(f'/thinking(turn {self.turns_num})'.center(80, '-'))

            with open("agent_tools_description_and_full_history.txt", "w", encoding="utf-8") as file:
                file.write(self.agent_tools_description_and_full_history)

            return answer_this_turn

        print(f'/thinking(turn {self.turns_num})'.center(80, '-'))
        return answer_this_turn

    def action(self, in_answer):
        dgreen(f'action(turn {self.turns_num})'.center(80, '='))
        # --------------------------- call tool ---------------------------
        action_result = ''

        # print(f'in_answer1: {in_answer}')
        # 去掉'[观察]'及后续内容
        in_answer = in_answer.split('[观察]')
        if len(in_answer)>1:
            in_answer.pop()
        in_answer = ''.join(in_answer)
        # print(f'in_answer2: {in_answer}')
        tool_name = Base_Tool.extract_tool_name_from_answer(in_answer)

        # print(f'=============================thoughts=============================')
        # print(in_thoughts)
        # print(f'-----------------------------thoughts-----------------------------')
        dblue(f'【tool_name: "{tool_name}"】'.center(40, '-'))

        if self.registered_tool_instances_dict.get(tool_name):
            dict_string = extract_dict_string(in_answer)
            dict = json5.loads(dict_string)
            callback_tool_paras_dict = dict['tool_parameters']
            action_result = self.registered_tool_instances_dict[tool_name].call(
                callback_tool_paras_dict=callback_tool_paras_dict,  # 将agent生成的调用tool的参数传给tool
                callback_agent_config=self.agent_config,            # 将agent配置传给tool
                callback_agent_id=self.agent_id,                    # 将agent_id传给tool
            )
        else:
            self.status_print('未选择任何工具。')
        # --------------------------- call tool ---------------------------

        self.status_print(f'调用工具的行动结果为: \n{action_result}')
        self.output_log_stream_chunk(f'\n调用工具的行动结果为: \n{action_result}\n')

        # dblue(f'action_result(turn {self.turns_num})'.center(80, '='))
        # dblue(action_result)
        # dblue(f'/action_result(turn {self.turns_num})'.center(80, '-'))

        dgreen(f'/action(turn {self.turns_num})'.center(80, '-'))
        return action_result

    def observation(self, in_action_result=''):
        self.agent_tools_description_and_full_history += f'[观察]{in_action_result}'

        # dcyan(f'==============================full_history(turn {self.turns_num})=======================')
        # dcyan(self.agent_tools_description_and_full_history)
        # dcyan(f'-----------------------------/full_history(turn {self.turns_num})-----------------------')

        # with open("agent_tools_description_and_full_history.txt", "w", encoding="utf-8") as file:
        #     file.write(self.agent_tools_description_and_full_history)

        # print(f'============================prompt start============================\n')
        # print(f'{self.prompt}\n------------------------prompt end------------------------')

def main():
    from agent.tools.search_tool import Search_Tool
    tools=[Search_Tool, Url_Content_QA_Tool]
    # tools=[Search_Tool, Code_Tool, Energy_Investment_Plan_Tool, QA_Url_Content_Tool]

    # tools=[Code_Tool]
    # print(tools)
    exit = False
    cont = False
    while True:
        print("请输入多行信息并以Ctrl+D确认，或输入'exit'结束：")
        query = ''
        lines = []
        while True:
            try:
                line = input()
                if line.strip()=='exit':
                    exit = True
                    break
                lines.append(line)
            except EOFError:
                query = '\n'.join(lines)
                if query.strip()=='':
                    # 输入为空
                    cont = True
                    
                break
        if exit:
            break
        if cont:
            cont = False
            continue
            
        agent = Tool_Agent(query=query, tool_classes=tools)
        agent.init()
        success = agent.run()
        if success:
            dblue(f"\n[运行结果]成功。")
        else:
            dred(f"\n[运行结果]失败，请进一步优化问题的描述。")

def main2():
    from agent.tools.search_tool import Search_Tool
    tools=[Search_Tool]
    query = '搜索网络告诉我莱温斯基是谁？'
    agent = Tool_Agent(query=query, tool_classes=tools)
    agent.init()
    success = agent.run()
    if success:
        dblue(f"\n[运行结果]成功。")
    else:
        dred(f"\n[运行结果]失败，请进一步优化问题的描述。")
    print(f'最终答复:')
    print(agent.get_final_answer())

def main_folder():
    import config
    from agent.tool_agent import Tool_Agent
    from agent.tools.folder_tool import Folder_Tool
    from agent.agent_config import Config

    tools=[Folder_Tool]
    print(f'os: "{config.get_os()}"')
    if config.get_os()=='windows':
        # query = r'请告诉我"file_to_find.txt"在"d:\demo\"文件夹的哪个具体文件夹中'
        query = r'请告诉我"file_to_find.txt"在"y:\demo\"文件夹的哪个具体文件夹中'
    else:
        query = r'请告诉我"./"文件夹里有哪些文件，不作任何解释，直接输出结果'

    config = Config(
        base_url='http://powerai.cc:28001/v1',  # llama-4-400b#llama-4-400b
        # base_url='http://powerai.cc:38001/v1',   #deepseek-r1-671b
        api_key='empty',
    )

    agent = Tool_Agent(
        query=query,
        tool_classes=tools,
        agent_config=config
    )
    agent.init()
    success = agent.run()

def main_table():
    import config
    from agent.tool_agent import Tool_Agent
    from agent.tools.table_tool import Table_Tool
    from agent.agent_config import Config

    tools=[Table_Tool]
    # tools=[Folder_Tool, Search_Tool]
    # query = '第一步：搜索"万向创新聚能城"，返回万向创新聚能城所在城市；第二步搜索所在城市，返回该城市概况'
    query=''
    print(f'os: "{config.get_os()}"')
    if config.get_os()=='windows':
        # query = r'请返回y:/demo/负荷及平衡.xlsx里的"负荷预测"标签中的表格数据，不绘制表格'
        query = r'请返回d:/demo/负荷及平衡.xlsx里的"负荷预测"标签中的表格数据，不绘制表格'
    else:
        query = r'请告诉我y:/demo/负荷及平衡.xlsx里的"负荷预测"标签中的表格数据.'

    config = Config(
        # base_url='http://powerai.cc:28001/v1',  # llama-4-400b#llama-4-400b
        base_url='http://powerai.cc:28002/v1',  # qwen3-235b
        # base_url='http://powerai.cc:38001/v1',   #deepseek-r1-671b
        # base_url='http://powerai.cc:8001/v1',   #qwen3-30b
        api_key='empty',
    )
    agent = Tool_Agent(
        query=query,
        tool_classes=tools,
        agent_config=config,
    )
    agent.init()
    success = agent.run()

if __name__ == "__main__":
    # main()
    # main2()
    # table_main()

    # main_folder()
    main_table()
