from tools.llm.api_client import LLM_Client, Concurrent_LLMs, Async_LLM
from agent.tool_agent_prompts import PROMPT_REACT
from agent.tool_agent_prompts import Base_Tool, Search_Tool, Code_Tool
from utils.extract import extract_code, extract_dict_string
import torch

class Tool_Agent():
    def __init__(self, in_query, in_tool_classes, in_human=True):
        self.llm = None
        self.prompt = ''
        self.query=in_query
        self.tool_descs=''
        self.tool_names=[]

        self.tool_classes = in_tool_classes
        self.human = in_human    # 是否和human交互
        self.action_stop = ['【观察】']
        self.observation_stop = ['【观察】']

    def init(self):
        self.llm = LLM_Client(temperature=0, history=False, print_input=False, max_new_tokens=1048)
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
            if '【最终答复】' in thoughts:
                return True

            if i>0:
                if self.human:
                    human_input = input('【暂停】是否需要继续, y/n?')
                    if human_input=='y':
                        pass
                    else:
                        return False

            # 2、行动
            action_result = self.action(in_thoughts=thoughts)
            # 3、观察
            self.observation(in_action_result=action_result)
            
        return False

    def thinking(self):
        thoughts = self.llm.ask_prepare(self.prompt, in_stop=self.action_stop).get_answer_and_sync_print()
        if '【最终答复】' in thoughts:
            return thoughts
            
        self.prompt += '\n' + thoughts + '】'
        print(f'============================prompt start============================\n')
        print(f'{self.prompt}\n------------------------prompt end------------------------')
        return thoughts

    def action0(self, in_thoughts):
        # --------------------------- call tool ---------------------------
        action_result = ''
        dict_string = extract_dict_string(in_thoughts)
        print('+++++++++++++++++++++')
        print(f'dict_string:')
        print(f'{dict_string}')
        print('+++++++++++++++++++++')
        if not dict_string:
            action_result = '【错误】工具参数未写完整！'
            return action_result
        if 'code_tool' in dict_string:
            print('选择了【code_tool】')
            code = extract_code(dict_string)
            if code:
                print(f'【code_tool】输入的程序为：\n{code}\n')
                action_result = execute_python_code_in_docker(code)
                if action_result=='':
                    action_result = 'code_tool未输出有效信息，可能是因为没有用print输出结果。'
        elif 'search_tool' in dict_string:
            print('选择了【search_tool】')
        else:
            print('未选择任何工具。')
        # --------------------------- call tool ---------------------------

        print(f'【行动结果】\n{action_result}')
        return action_result

    def action(self, in_thoughts):
        # --------------------------- call tool ---------------------------
        action_result = ''
        tool_name = Base_Tool.extract_tool_name(in_thoughts)

        if 'code_tool'==tool_name:
            print('选择了【code_tool】')
            tool = Code_Tool()
            action_result = tool.call(in_thoughts)
            if action_result=='':
                action_result = 'code_tool未输出有效信息，可能是因为没有用print输出结果。'
            print(f'action_result = "{action_result}"')
        elif 'search_tool'==tool_name:
            print('选择了【search_tool】')
        else:
            print('未选择任何工具。')
        # --------------------------- call tool ---------------------------

        print(f'【行动结果】\n{action_result}')
        return action_result

    def observation(self, in_action_result=''):
        self.prompt += '工具调用结果为：' + in_action_result
        # print(f'============================prompt start============================\n')
        # print(f'{self.prompt}\n------------------------prompt end------------------------')

def main():
    # torch.cuda.manual_seed_all(20000)
    LLM_Client.Set_All_LLM_Server('http://127.0.0.1:8002/v1')
    # LLM_Client.Set_All_LLM_Server('http://127.0.0.1:8001/v1')
    tools=[Search_Tool, Code_Tool]
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
            print(f"【运行结果】成功。")
        else:
            print(f"【运行结果】失败，请进一步优化问题的描述。")
            
if __name__ == "__main__":
    ###
    main()