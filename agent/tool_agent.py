from tools.llm.api_client import LLM_Client, Concurrent_LLMs, Async_LLM, Set_All_LLM_Server
from agent.tool_agent_prompts import PROMPT_REACT
from agent.tool_agent_prompts import Search_Tool, Code_Tool
from tools.exec_code.exec_python_linux import execute_python_code_in_docker
from utils.extract import extract_code, extract_dict_string
import torch

class Tool_Agent():
    def __init__(self, in_query, in_tool_classes):
        self.llm = None
        self.prompt = ''
        self.query=in_query
        self.tool_descs=''
        self.tool_names=[]

        self.tool_classes = in_tool_classes
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

    def run(self, in_max_retry=3):
        for i in range(in_max_retry):
            # 1、思考
            thoughts = self.thinking()
            if '【最终答复】' in thoughts:
                return True

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

    def action(self, in_thoughts):
        # --------------------------- call tool ---------------------------
        action_result = ''
        dict_string = extract_dict_string(in_thoughts)
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

    def observation(self, in_action_result=''):
        self.prompt += '工具调用结果为：' + in_action_result
        # print(f'============================prompt start============================\n')
        # print(f'{self.prompt}\n------------------------prompt end------------------------')

def main():
    # torch.cuda.manual_seed_all(20000)
    # Set_All_LLM_Server('http://127.0.0.1:8002/v1')
    Set_All_LLM_Server('http://127.0.0.1:8001/v1')
    tools=[Search_Tool, Code_Tool]
    # tools=[Code_Tool]   
    # print(tools)
    exit = False
    while True:
        print("请输入多行数据，输入结束后使用Ctrl+D（Unix/Linux）或Ctrl+Z（Windows）结束：")
        query = ''
        lines = []
        while True:
            try:
                line = input()
                if line=='exit':
                    exit = True
                    break
                lines.append(line)
            except EOFError:
                query = '\n'.join(lines)
                break
        if exit:
            break
            
        agent = Tool_Agent(in_query=query, in_tool_classes=tools)
        agent.init()
        success = agent.run()
        if success:
            print(f"【运行结果】成功。")
        else:
            print(f"【运行结果】失败，请进一步优化问题的描述。")
            
if __name__ == "__main__":
    main()