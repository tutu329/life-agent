from tools.llm.api_client import LLM_Client, Concurrent_LLMs, Async_LLM
from agent.tool_agent_prompts import PROMPT_REACT
from agent.tool_agent_prompts import Search_Tool, Code_Tool

class Tool_Agent():
    def __init__(self, in_query, in_tool_classes):
        self.llm = None
        self.prompt = ''
        self.query=in_query
        self.tool_descs=''
        self.tool_names=[]

        self.tool_classes = in_tool_classes

    def init(self):
        self.llm = LLM_Client(temperature=0)
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

    def run(self):
        # print(f'【prompt】\n{self.prompt}')
        res = self.llm.ask_prepare(self.prompt, in_stop=['Observation:']).get_answer_and_sync_print()
        return res

def main():
    tools=[Search_Tool, Code_Tool]
    print(tools)
    agent = Tool_Agent(in_query='今天是几号？', in_tool_classes=tools)
    agent.init()
    result = agent.run()
    # print(result)

if __name__ == "__main__":
    main()