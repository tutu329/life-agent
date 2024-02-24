from tools.llm.api_client import LLM_Client, Concurrent_LLMs, Async_LLM
from agent.tool_agent_prompts import PROMPT_REACT
from agent.tool_agent_prompts import Base_Tool, Search_Tool, Code_Tool, Energy_Investment_Plan_Tool
from utils.extract import extract_code, extract_dict_string
import torch

class Tool_Agent():
    def __init__(self,
                 in_query,
                 in_tool_classes,
                 in_human=True,
                 inout_status_list=None,
                 in_output_stream_buf=None,
                 inout_output_list=None,
                 in_status_stream_buf=None,
                 ):
        self.llm = None
        self.prompt = ''
        self.query=in_query
        self.tool_descs=''
        self.tool_names=[]

        self.tool_classes = in_tool_classes
        self.human = in_human    # 是否和human交互
        self.action_stop = ['【观察】']
        self.observation_stop = ['【观察】']

        self.ostream = in_output_stream_buf   # 最终结果输出的stream
        self.sstream = in_status_stream_buf   # 中间状态输出的stream

        self.status_list = inout_status_list     # 状态历史
        self.output_list = inout_output_list     # 输出历史

        self.__finished_keyword = '【最终答复】'

    # 最终结果输出
    def output_print(self, in_string):
        if self.ostream is not None:
            self.ostream(in_string)

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

    # 最终结果stream输出
    def output_stream(self, in_chunk, in_full_response):
        if self.ostream is not None:
            self.ostream(in_full_response)
        else:
            print(in_chunk, end='', flush=True)

    # 中间状态stream输出(注意：streamlit的status不支持stream输出，只能打印)
    def status_stream(self, in_chunk, in_full_response):
        if self.sstream is not None:
            # self.sstream(in_chunk)
            pass
        else:
            print(in_chunk, end='', flush=True)

    def init(self):
        self.llm = LLM_Client(temperature=0, history=False, print_input=False, max_new_tokens=1024)
        self.prompt = PROMPT_REACT

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

        self.prompt = self.prompt.format(tool_descs=self.tool_descs, tool_names=self.tool_names, query=self.query)

    def run(self, in_max_retry=5):
        for i in range(in_max_retry):
            # 1、思考
            thoughts = self.thinking()
            if self.__finished_keyword in thoughts:
                return True

            # if i>0:
            #     if self.human:
            #         human_input = input('【暂停】是否需要继续, y/n?')
            #         if human_input=='y':
            #             pass
            #         else:
            #             return False

            # 2、行动
            action_result = self.action(in_thoughts=thoughts)
            # 3、观察
            self.observation(in_action_result=action_result)

        return False

    def _thoughts_stream_output(self, gen):
        thoughts = ''
        i=0
        # stream输出
        for chunk in gen:
            thoughts +=chunk
            if self.__finished_keyword in thoughts:
                # 最终结果stream输出
                self.output_stream(chunk, thoughts.replace(self.__finished_keyword, ''))
            else:
                # 中间状态stream输出(streamlit的status不支持stream输出，所以这里为空操作，并在后续作status_print处理)
                # self.status_stream(chunk, thoughts)
                pass
                if '\n' in thoughts:
                    # 输出已经有\n的内容
                    print_content = thoughts.split('\n')[i]
                    i += 1
                    print(f'=================print_content: {print_content}')
                    self.status_print(print_content)
                    if self.status_list is not None:
                        self.status_list.append(print_content)
                    # 删除第一个\n前的内容
                    # remain_content = thoughts.split('\n')
                    # remain_content.pop(0)
                    # print(f'=================remain_content: {remain_content}')
                    # thoughts = '\n'.join(remain_content)
        # 添加输出历史
        if self.__finished_keyword in thoughts:
            # 最终结果输出历史
            if self.output_list is not None:
                s = thoughts.replace(self.__finished_keyword, '')
                # print(f'self.output_list.append: {s}')
                self.output_list.append(thoughts.replace(self.__finished_keyword, ''))
        else:
            # 中间状态输出历史
            self.status_print(thoughts) # streamlit的status无法stream输出，只能这里print输出
            if self.status_list is not None:
                # print(f'self.status_list.append: {thoughts}')
                self.status_list.append(thoughts)

        return thoughts

    def thinking(self):
        gen = self.llm.ask_prepare(self.prompt, in_stop=self.action_stop).get_answer_generator()
        # thoughts = ''

        thoughts = self._thoughts_stream_output(gen)

        if self.__finished_keyword in thoughts:
            return thoughts

        self.prompt += '\n' + thoughts + '】'
        # self.status_print(f'============================prompt start============================\n')
        # self.status_print(f'{self.prompt}\n------------------------prompt end------------------------')
        return thoughts

    def action(self, in_thoughts):
        # --------------------------- call tool ---------------------------
        action_result = ''
        tool_name = Base_Tool.extract_tool_name(in_thoughts)

        if 'code_tool'==tool_name:
            self.status_print('选择了【code_tool】')
            tool = Code_Tool()
            action_result = tool.call(in_thoughts)
            if action_result=='':
                action_result = 'code_tool未输出有效信息，可能是因为没有用print输出结果。'
            # self.status_print(f'action_result = "{action_result}"')
        elif 'search_tool'==tool_name:
            self.status_print('选择了【search_tool】')
            tool = Search_Tool()
            action_result = tool.call(in_thoughts)
            # self.status_print(f'action_result = "{action_result}"')
        elif 'energy_investment_plan_tool'==tool_name:
            self.status_print('选择了【energy_investment_plan_tool】')
            tool = Energy_Investment_Plan_Tool()
            action_result = tool.call(in_thoughts)
            # self.status_print(f'action_result = "{action_result}"')
        else:
            self.status_print('未选择任何工具。')
        # --------------------------- call tool ---------------------------

        self.status_print(f'【行动结果】\n{action_result}')
        return action_result

    def observation(self, in_action_result=''):
        self.prompt += '工具调用结果为：' + in_action_result
        # print(f'============================prompt start============================\n')
        # print(f'{self.prompt}\n------------------------prompt end------------------------')

def main():
    # torch.cuda.manual_seed_all(20000)
    # LLM_Client.Set_All_LLM_Server('http://127.0.0.1:8002/v1')
    LLM_Client.Set_All_LLM_Server('http://116.62.63.204:8001/v1')
    tools=[Search_Tool, Code_Tool, Energy_Investment_Plan_Tool]
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
        success = agent.run_yield()
        if success:
            print(f"【运行结果】成功。")
        else:
            print(f"【运行结果】失败，请进一步优化问题的描述。")
            
if __name__ == "__main__":
    #hi
    main()