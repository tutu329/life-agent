import os
import importlib.util
import inspect

from typing import List, Dict, Any, Type
from pydantic import BaseModel
from uuid import uuid4

from agent.core.agent_config import Config
from config import dred,dgreen,dblue,dcyan,dyellow

class Registered_Tool_Data(BaseModel):
    tool_id: str
    name: str
    description: str
    parameters: List[Dict[str, str]]
    tool_class: Type     # tool类对象（非实例）

# 全局存储tools的注册( tool_id <--> Tool_Data )
g_registered_tools_dict: Dict[str, Registered_Tool_Data] = {}

# server用的tool注册管理，tool_name相当于id(server启动时调用)
def server_register_all_tool():
    all_tools_data_list = _get_all_tools_data()

    for tool_data in all_tools_data_list:
        tool_class = tool_data['tool_class']
        if isinstance(tool_class, type):
            # 如果tool_class是一个class
            tool_instance = tool_class()

            # 生成全局唯一的tool_id
            tool_id = str(uuid4())

            # 查找tool
            tool_data = Registered_Tool_Data(
                tool_id=tool_id,
                name=tool_data['name'],
                description=tool_data['description'],
                parameters=tool_data['parameters'],
                tool_class=tool_class,
            )

            # server端注册tool
            g_registered_tools_dict[tool_id] = tool_data

    print_all_registered_tools()
    return g_registered_tools_dict

def print_all_registered_tools():
    print('---------------------g_registered_tools_dict-----------------------')
    for k,v in g_registered_tools_dict.items():
        print(f'tool_id: {v.tool_id}', end=' ')
        print(f'name: {v.name}')
        # print(f'description: {v.description}', end=' \t')
        # print(f'tool_class: {v.tool_class}')
    print('--------------------/g_registered_tools_dict-----------------------')

def server_get_tool_data_by_id(tool_id):
    return g_registered_tools_dict[tool_id]

# client第一步：获取所有已注册tool
def client_get_all_registered_tool_data_list():
    data_list = []
    for k,v in g_registered_tools_dict.items():
        data_list.append(v)
    return data_list

# client用的tool注册管理，必须通过server生成的tool_id唯一化
def client_register_fastapi_tool(
    name,           # tool的name
    description,    # tool的description
    parameters,     # tool的parameters
    fastapi_url,    # tool的fastapi的url地址
)->str:                     # 返回：str(uuid4())
    tool_id = str(uuid4())

    return tool_id

# client用的tool注册管理，必须通过server生成的tool_id唯一化
def client_register_agent_as_tool(
    agent_config:Config,    # 该agent的base_url, api_key, model_id等信息
    tools_name_list,        # 该agent所需tool的name_list
    as_tool_name,           # 该agent作为tool的name
    as_tool_description,    # 该agent作为tool的description
)->str:                     # 返回：str(uuid4())
    tool_id = str(uuid4())

    return tool_id

# server启动后的第一步：从tools文件夹获取所有可用的tools（后续第二步，才是将所有tool注册，并获取对应tool_id）
def _get_all_tools_data() -> List[Dict[str, Any]]:
    """
    获取 tools 文件夹下所有 py 文件里的 tool 信息

    Returns:
        List[Dict]: 包含所有 tool 信息的列表，每个元素包含：
            - name: tool 名称
            - description: tool 描述
            - parameters: tool 参数
            - tool_class: tool 类对象（非实例）
    """
    tools_info = []
    tools_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tools')

    # 遍历 tools 文件夹下的所有 py 文件
    for filename in os.listdir(tools_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]  # 去掉 .py 后缀
            file_path = os.path.join(tools_dir, filename)

            try:
                # 动态导入模块
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # 查找模块中的类
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # 检查是否是在当前模块中定义的类（不是导入的类）
                    if (obj.__module__ == module_name and
                            hasattr(obj, 'name') and
                            hasattr(obj, 'description') and
                            hasattr(obj, 'parameters')):
                        tool_info = {
                            'name': obj.name,
                            'description': obj.description,
                            'parameters': obj.parameters,
                            'tool_class': obj  # 返回类对象本身，不是实例
                        }
                        tools_info.append(tool_info)

            except Exception as e:
                print(f"尝试动态导入 {filename} 失败: {e}")
                # 如果动态导入失败，尝试通过文本解析提取信息
                try:
                    tool_info = _extract_tool_info_from_file(file_path, module_name)
                    if tool_info:
                        tools_info.append(tool_info)
                except Exception as parse_error:
                    print(f"解析 {filename} 失败: {parse_error}")
                continue

    return tools_info


def _extract_tool_info_from_file(file_path: str, module_name: str) -> Dict[str, Any]:
    """
    从文件中通过文本解析提取工具信息并创建类对象
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 尝试解析 AST
    try:
        tree = ast.parse(content)
    except:
        return None

    for node in ast.walk(tree):
        if (isinstance(node, ast.ClassDef) and
                any(isinstance(base, ast.Name) and base.id == 'Base_Tool'
                    for base in node.bases)):

            # 找到继承自 Base_Tool 的类
            class_name = node.name

            # 提取类属性
            name = None
            description = None
            parameters = None

            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name):
                            if target.id == 'name' and isinstance(item.value, ast.Constant):
                                name = item.value.value
                            elif target.id == 'description' and isinstance(item.value, ast.Constant):
                                description = item.value.value
                            elif target.id == 'parameters':
                                # 尝试提取 parameters
                                try:
                                    parameters = ast.literal_eval(item.value)
                                except:
                                    parameters = "无法解析参数"

            if name and description:
                # 动态创建真正的类对象
                class_attrs = {
                    'name': name,
                    'description': description,
                    'parameters': parameters or [],
                    '__init__': lambda self: None,
                    '__module__': module_name
                }

                # 创建类对象
                tool_class = type(class_name, (), class_attrs)

                return {
                    'name': name,
                    'description': description,
                    'parameters': parameters or [],
                    'tool_class': tool_class  # 返回真正的类对象
                }

    return None

def get_tools_class(tool_names):
    all_tools = _get_all_tools_data()

    tools_class_list = []
    for tool_name in tool_names:
        for tool in all_tools:
            if tool['name'] == tool_name:
                dgreen(tool_name)
                tools_class_list.append(tool['tool_class'])
                break
        else:   # python的for-else机制：内层循环正常结束（没有 break）时才执行 else 块
            dred(f'get_tool_class未找到tool_name("{tool_name}")')
            raise Exception(f'get_tool_class未找到tool_name("{tool_name}")')

    return tools_class_list

def main_test_get_all_tools():
    from pprint import pprint
    # 获取所有工具信息
    all_tools = _get_all_tools_data()

    print(f"找到 {len(all_tools)} 个工具:")
    print(f'----------------------------all_tools info----------------------------\n')
    pprint(all_tools)
    print(f'----------------------------all_tools info----------------------------')

    for tool in all_tools:
        print(f"- {tool['name']}: {tool['tool_class'].__name__}")

    # 提取工具类对象，可以这样使用：
    # tools = [tool['tool_class'] for tool in all_tools]
    # 例如：tools = [Code_Tool, Database_Tool, ...]
    tools = [tool['tool_class'] for tool in all_tools]
    print(f"\n所有tool的Class列表: {[cls.__name__ for cls in tools]}")

def main_test_agent():
    from agent.core.agent_config import Config
    from agent.core.tool_agent import Tool_Agent
    # tool_names = ['Folder_Tool']
    tool_names = ['Human_Console_Tool', 'Folder_Tool']
    class_list = get_tools_class(tool_names)
    print(class_list)

    tools = class_list

    # 创建配置
    config = Config(
        base_url='https://api.deepseek.com/v1',
        api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
        model_id='deepseek-chat'
    )

    agent = Tool_Agent(
        query='当前目录下有哪些文件',
        tool_classes=tools,
        agent_config=config
    )

    agent.init()
    success = agent.run()

def main_test_server_start():
    from pprint import pprint
    from agent.core.tool_agent import client_run_agent
    server_register_all_tool()

    tool_data_list = client_get_all_registered_tool_data_list()

    pprint(tool_data_list)

    tool_names = ['Human_Console_Tool', 'Folder_Tool']
    config = Config(
        base_url='https://api.deepseek.com/v1',
        api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
        model_id='deepseek-chat'
    )
    query='当前目录下有哪些文件'
    client_run_agent(query=query, agent_config=config, tool_names=tool_names)


# 使用示例
if __name__ == "__main__":
    # main_test_get_all_tools()
    # main_test_agent()
    main_test_server_start()
