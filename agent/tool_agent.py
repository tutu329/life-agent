from tools.llm.api_client import LLM_Client, Concurrent_LLMs, Async_LLM
from agent.base_tool import PROMPT_REACT
from agent.base_tool import Base_Tool
from utils.extract import extract_code, extract_dict_string
from colorama import Fore, Back, Style

from config import dred, dgreen, dblue, dcyan, dyellow

from agent.tools.code_tool import Code_Tool
from agent.tools.energy_investment_plan_tool import Energy_Investment_Plan_Tool
from agent.tools.folder_tool import Folder_Tool
from agent.tools.search_tool import Search_Tool
from agent.tools.url_content_qa_tool import Url_Content_QA_Tool

class Tool_Agent():
    def __init__(self,
                 in_query,
                 in_tool_classes,
                 in_human=True,
                 inout_status_list=None,
                 in_output_stream_buf=None, # 最终答复stream输出的func
                 in_output_end=None,        # 最终答复输出end的func
                 in_output_stream_to_console=False, # 最终答复是否stream输出到console
                 in_output_stream_use_chunk=True,   # 最终答复stream输出是否采用chunk方式，还是full_string方式
                 inout_output_list=None,
                 in_status_stream_buf=None,
                 ):
        self.llm = None
        self.agent_desc_and_action_history = ''
        self.query=in_query
        self.tool_descs=''
        self.tool_names=[]

        self.tool_classes = in_tool_classes
        # 创建一个字典，将工具名称映射到其实例
        self.registered_tool_instances_dict = {}
        for tool_cls in in_tool_classes:
            tool_instance = tool_cls()
            tool_name = tool_cls.__name__
            self.registered_tool_instances_dict[tool_name] = tool_instance

        self.human = in_human    # 是否和human交互
        self.action_stop = ['[观察]']
        self.observation_stop = ['[观察]']
        self.response_stop = ['[观察]']
        # self.response_stop = ['<结束>']
        # self.response_stop = ['<res_stop>']

        self.ostream_func = in_output_stream_buf            # 最终结果stream输出的的func
        self.ostream_end_func = in_output_end               # 最终结果stream输出的end的func
        self.ostream_use_chunk = in_output_stream_use_chunk # 最终结果输出方式：chunk还是full_string
        self.output_stream_to_console = in_output_stream_to_console
        self.sstream = in_status_stream_buf                 # 中间状态输出的stream

        self.status_list = inout_status_list     # 状态历史
        self.output_list = inout_output_list     # 输出历史

        self.__finished_keyword = '最终答复'
        self.final_answer = ''

    # 最终结果输出
    def output_print(self, in_string):
        if self.ostream_func is not None:
            self.ostream_func(in_string)

            if self.output_list is not None:
                self.output_list.append(in_string)
        else:
            print(in_string)

    # 中间状态输出
    def status_print(self, in_string):
        if self.sstream is not None:
            self.sstream(in_string)

            if self.status_list is not None:
                self.status_list.append(in_string)
        else:
            print(in_string)

    # 最终结果stream输出full_string
    def output_stream_full_string(self, in_full_response):
        if self.ostream_func is not None:
            self.ostream_func(in_full_response)

    # 最终结果stream输出chunk，注意：要确保chunk中没有'[最终答复]'或'终答复]'
    def output_stream_chunk(self, chunk, **kwargs):
        if self.ostream_func is not None:
            self.ostream_func(chunk, **kwargs)

    # 中间状态stream输出(注意：streamlit的status不支持stream输出，只能打印)
    def status_stream(self, in_chunk, in_full_response):
        if self.sstream is not None:
            # self.sstream(in_chunk)
            pass
        else:
            print(in_chunk, end='', flush=True)

    def init(self):
        self.llm = LLM_Client(temperature=0, history=False, print_input=False, max_new_tokens=2048)
        self.agent_desc_and_action_history = PROMPT_REACT

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

        self.agent_desc_and_action_history = self.agent_desc_and_action_history.format(tool_descs=self.tool_descs, tool_names=self.tool_names, query=self.query)

    def get_final_answer(self):
        return self.final_answer

    def _parse_final_answer(self, answer):
        # self.__finished_keyword = '最终答复'
        # 去掉'[最终答复]'及之前的内容
        self.final_answer = answer.split(f'[{self.__finished_keyword}]')[-1]

    def run(self, in_max_retry=5):
        for i in range(in_max_retry):
            # 1、思考
            answer_this_turn = self.thinking()
            if self.__finished_keyword in answer_this_turn:
                self._parse_final_answer(answer_this_turn)
                return True

            # if i>0:
            #     if self.human:
            #         human_input = input('[暂停]是否需要继续, y/n?')
            #         if human_input=='y':
            #             pass
            #         else:
            #             return False

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
            thoughts +=chunk
            thoughts_copy_to_print +=chunk
            if f'[{self.__finished_keyword}]' in thoughts:
                # 最终结果stream输出
                if self.ostream_use_chunk:
                    # 采用chunk输出，chunk = string_this_turn - string_last_turn
                    str_this_turn = thoughts.split(f'[{self.__finished_keyword}]')[-1]
                    # dyellow(f'-----> "{str_this_turn}"')
                    if self.output_stream_to_console:
                        # 输出到console
                        self.output_stream_chunk(
                            str_this_turn.split(str_last_turn)[-1] if str_last_turn != '' else str_this_turn ,
                            end='',
                            flush=True
                        )
                    else:
                        # 输出到如word文档中
                        self.output_stream_chunk( str_this_turn.split(str_last_turn)[-1] if str_last_turn != '' else str_this_turn )
                    str_last_turn = str_this_turn
                else:
                    # 采用full_string输出
                    self.output_stream_full_string(thoughts)
                    # self.output_stream(chunk, thoughts.replace(self.__finished_keyword, ''))
            else:
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

        # stream输出最后的end
        if self.ostream_end_func:
            self.ostream_end_func()

        # 添加输出历史
        if self.__finished_keyword in thoughts:
            # 最终结果输出历史
            if self.output_list is not None:
                self.output_list.append(thoughts)
                # self.output_list.append(thoughts.replace(self.__finished_keyword, ''))
        else:
            # 中间状态输出历史
            # self.status_print(thoughts) # streamlit的status无法stream输出，只能这里print输出
            if self.status_list is not None:
                # print(f'self.status_list.append: {thoughts}')
                self.status_list.append(thoughts)

        return thoughts

    def thinking(self):
        print(f'****************************************thinking()***********************************************')
        # print(f'原始his: {self.agent_desc_and_action_history}', flush=True)
        dred(f'self.response_stop: "{self.response_stop}"')
        gen = self.llm.ask_prepare(self.agent_desc_and_action_history, stop=self.response_stop).get_answer_generator()
        # gen = self.llm.ask_prepare(self.agent_desc_and_action_history, in_stop=self.action_stop).get_answer_generator()
        # thoughts = ''

        answer_this_turn = self._thoughts_stream_output(gen)

        if self.__finished_keyword in answer_this_turn:
            print(Fore.GREEN, flush=True)
            dblue(f'=============================answer=============================')
            dblue(answer_this_turn)
            dblue(f'-----------------------------answer-----------------------------')

            print(f'----------------------------------------thinking()-----------------------------------------------')
            return answer_this_turn

        self.agent_desc_and_action_history += '\n' + answer_this_turn
        # self.agent_desc_and_action_history += '\n' + answer_this_turn + ']'
        # self.status_print(f'============================prompt start============================\n')
        # self.status_print(f'{self.prompt}\n------------------------prompt end------------------------')
        dblue(f'=============================answer=============================')
        dblue(answer_this_turn)
        dblue(f'-----------------------------answer-----------------------------')

        print(f'----------------------------------------thinking()-----------------------------------------------')
        return answer_this_turn

    def action(self, in_answer):
        dgreen(f'****************************************action()***********************************************')

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
        dblue(f'--------------【tool_name: "{tool_name}"】--------------')

        # if 'Code_Tool'==tool_name:
        #     self.status_print('选择了[code_tool]')
        #     tool = Code_Tool()
        #     action_result = tool.call(in_answer)
        #     if action_result=='':
        #         action_result = 'code_tool未输出有效信息，可能是因为调用code_tool时，输入的代码没有用print输出结果。'
        #     # self.status_print(f'action_result = "{action_result}"')
        # elif 'Search_Tool'==tool_name:
        #     self.status_print('选择了[search_tool]')
        #     tool = Search_Tool()
        #     action_result = tool.call(in_answer)
        # elif 'Energy_Investment_Plan_Tool'==tool_name:
        #     self.status_print('选择了[energy_investment_plan_tool]')
        #     tool = Energy_Investment_Plan_Tool()
        #     action_result = tool.call(in_answer)
        # elif 'QA_Url_Content_Tool'==tool_name:
        #     self.status_print('选择了[qa_url_content_tool]')
        #     tool = QA_Url_Content_Tool()
        #     action_result = tool.call(in_answer)
        # else:
        if self.registered_tool_instances_dict.get(tool_name):
            action_result = self.registered_tool_instances_dict[tool_name].call(in_answer)
        else:
            self.status_print('未选择任何工具。')
        # --------------------------- call tool ---------------------------

        self.status_print(f'调用工具的行动结果为: \n{action_result}')

        dblue(f'=============================action_result=============================')
        dblue(action_result)
        dblue(f'-----------------------------action_result-----------------------------')
        return action_result

#     def observation(self, in_action_result=''):
#         # agent_desc_and_action_history去掉最后一个[观察]及其后续内容
#         kword = '[观察]'
#         last_his = self.agent_desc_and_action_history.split(kword)
#         last_his.pop()
#         last_his = kword.join(last_his)
#
#         # 构造观察数据
#         obs_result = '\n' + kword
#         obs_result += '''
# {{
#     'observer':'system',
#     'status':'system returned',
#     'result':'{result}',
# }}
# '''
#         obs_result = obs_result.format(result=in_action_result)
#         self.agent_desc_and_action_history = last_his + obs_result
#
#         print(Fore.CYAN, flush=True)
#         print(f'=============================action_history=============================', flush=True)
#         print(self.agent_desc_and_action_history, flush=True)
#         print(f'-----------------------------action_history-----------------------------', flush=True)
#         print(Style.RESET_ALL, flush=True)
#         # print(f'============================prompt start============================\n')
#         # print(f'{self.prompt}\n------------------------prompt end------------------------')
    def observation(self, in_action_result=''):
        # agent_desc_and_action_history去掉最后一个[观察]及其后续内容
        # kword = '[观察]'
        # last_his = self.agent_desc_and_action_history.split(kword)
        # last_his.pop()
        # last_his = kword.join(last_his)

        # 构造观察数据
        # obs_result = '\n' + kword
        # obs_result += f'[观察]{in_action_result}'

        # obs_result = obs_result.format(result=in_action_result)
        # self.agent_desc_and_action_history = last_his + obs_result



        self.agent_desc_and_action_history += f'[观察]{in_action_result}'

        dcyan(f'=============================action_history=============================')
        dcyan(self.agent_desc_and_action_history)
        dcyan(f'-----------------------------action_history-----------------------------')
        # print(f'============================prompt start============================\n')
        # print(f'{self.prompt}\n------------------------prompt end------------------------')

def main():
    # torch.cuda.manual_seed_all(20000)
    # LLM_Client.Set_All_LLM_Server('http://127.0.0.1:8002/v1')
    # LLM_Client.Set_All_LLM_Server('http://116.62.63.204:8001/v1')

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
            
        agent = Tool_Agent(in_query=query, in_tool_classes=tools)
        agent.init()
        success = agent.run()
        if success:
            dblue(f"\n[运行结果]成功。")
        else:
            dred(f"\n[运行结果]失败，请进一步优化问题的描述。")

def main2():
    tools=[Search_Tool]
    query = '搜索网络告诉我莱温斯基是谁？'
    agent = Tool_Agent(in_query=query, in_tool_classes=tools)
    agent.init()
    success = agent.run()
    if success:
        dblue(f"\n[运行结果]成功。")
    else:
        dred(f"\n[运行结果]失败，请进一步优化问题的描述。")
    print(f'最终答复:')
    print(agent.get_final_answer())

def main3():
    tools=[Folder_Tool, Search_Tool]
    query = '第一步：搜索"万向创新聚能城"，返回万向创新聚能城所在城市；第二步搜索所在城市，返回该城市概况'
    # query = '请告诉我"y:\demo\依据"文件夹里有哪些文件，不作任何解释，直接输出结果'
    agent = Tool_Agent(
        in_query=query,
        in_tool_classes=tools,
        in_output_stream_buf=dyellow,
        in_output_stream_to_console=True,
    )
    agent.init()
    success = agent.run()

if __name__ == "__main__":
    # main()
    # main2()
    main3()
