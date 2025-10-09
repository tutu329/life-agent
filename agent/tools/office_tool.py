import time, json5, json, asyncio

from accelerate.commands.config.update import description
from streamlit import success

import config
from agent.core.agent_config import Agent_Config
from config import dred, dgreen, dcyan, dblue, dyellow
from utils.encode import safe_encode
from utils.extract import extract_chapter_no

from agent.tools.base_tool import Base_Tool
from agent.tools.legacy_protocol import Action_Result, Tool_Call_Paras
from agent.core.protocol import Agent_Tool_Result
from tools.doc.docx_para import DocxParser
from tools.doc.docx_outline import DocxOutlineExtractor

from utils.web_socket_manager import get_websocket_manager
from web_socket_server import Web_Socket_Server_Manager

from agent.tools.office_tool_uno_command.uno_command import Uno_Command, Uno_Color
from tools.llm.api_client import LLM_Client
import llm_protocol
from llm_protocol import LLM_Query_Paras

from pydantic import BaseModel

from agent.tools.protocol import Tool_Parameters, Tool_Property, Property_Type
from tools.llm.response_and_chatml_api_client import Response_Result, Tool_Request, Response_Request
from console import err

OFFICE_WS_CLIENT_ID = config.Agent.OFFICE_test_WS_CLIENT_ID

def _test_call_collabora_api(ws_server):
    while True:
        if OFFICE_WS_CLIENT_ID in ws_server.registered_client:
            break

        time.sleep(0.1)

    if OFFICE_WS_CLIENT_ID in ws_server.registered_client:
        # ------临时的websocket连接方式（选择第一个连接的客户端进行测试）------
        timeout = 30  # 等待30秒
        start_time = time.time()

        # 桥接collabora CODE接口
        command = {
            'type': 'office_operation',
            'operation': 'call_python_script',
            # 'agent_id': agent_id,
            # 'agent_id': top_agent_id,
            'data': {},
            'timestamp': int(time.time() * 1000)
        }
        # command = {
        #     'type': 'office_operation',
        #     'operation': 'call_python_script',
        #     # 'agent_id': agent_id,
        #     # 'agent_id': top_agent_id,
        #     'data': {},
        #     'timestamp': int(time.time() * 1000)
        # }
        params = {
            'formula': 'E = m cdot c^{2} int from a to b f(x) dx = F(b) - F(a)',
            # 'formula':'int_{a}^{b}f(x)dx = F(b)-F(a)',
            # 'formula':'E = m c^2',
            'as_inline': True,
            'base_font_height': 12,
        }
        # params = {
        #     'text':'hi every body4!\n hi every body5!',
        #     'font_name':'SimSun',
        #     'font_color':'blue',
        #     'font_size':12,
        # }
        command['data'] = {
            'cmd': 'insert_math',
            'params': params
        }
        # command['data'] = {
        #     'cmd':'insert_text',
        #     'params':params
        # }

        # 通过web-socket发送至前端
        success, message = _send_office_command_test(ws_server, command)
        print(f'command={command!r}')
        print(f'success={success!r}, message={message!r}')
        return success, message

def _send_office_command_test(ws, command):
    """向指定客户端发送命令（同步接口）"""
    # 创建新的事件循环发送命令
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _async_send_command(ws, command):
            try:
                command_json = json.dumps(command, ensure_ascii=False)

                # ------------------web_socket发送指令---------------------
                await ws.send_client(client_id=OFFICE_WS_CLIENT_ID, data=command_json)
                # await ws.send_client(client_id='1', data=command_json)
                # await ws.broadcast((command_json))
                # -----------------/web_socket发送指令---------------------

                # dgreen(f'_async_send_command()成功：client_id为"{client_id}".')
                return True, 'success'
            except Exception as e:
                return False, f'发送失败: {e}'

    try:
        success, message = loop.run_until_complete(_async_send_command(ws, command))
        return success, message
    except Exception as e:
        return False, f'发送失败: {e}'
    finally:
        loop.close()

class Prompt_Write_Chapter_Text(BaseModel):
    project_name            :str =''  # 项目名称
    project_key_demand      :str =''  # 项目核心需求
    project_outline         :str =''  # 项目完整提纲
    project_investment      :str =''  # 项目预期投资
    chapter_content_demand  :str =''  # 需编制的章节内容的编制要求
    chapter_template        :str =''  # 需编制的章节对应的章节模板内容

g_prompt_write_chapter_text = \
'''
<总体要求>
请严格根据【章节编制总体要求】、【项目名称】、【项目核心需求】、【报告完整提纲】、【项目预期投资水平】、【章节模板】的内容或要求，编写章节内容。
</总体要求>

<章节编制总体要求>
1、内容要求
    1）编制的是章节内容，而不是编制整个报告，因此要注意该章节内容在【报告完整提纲】中的大概定位，不要错误的编制应该其他章节编制的内容。
    2）章节内容的范围，应与【章节模板】一致或相符，绝对不能随意写入【章节模板】以外其他内容，也绝对不能提及【章节编制总体要求】、【项目名称】、【项目核心需求】、【报告完整提纲】、【项目预期投资水平】、【章节模板】等高于该章节层次的信息或与编制内容无关的信息，因为那样会破坏该章节内容组织和表述的合理性。
    3）章节内容的篇幅和形式，必须让文字段落在字数上占主导比例，不能让标题化的内容在字数上占主导比例。
    4）若给你提供的【章节模板】内容中包含了章节的标题如'2.1 xxx标题'这样，绝对不要把这个'2.1 xxx标题'再进行输出（因为一般之前已经由其他专用工具在文档中插入了你所编制的章节的序号和标题）。
2、格式要求：
    1）编制的文本都会写入docx文档中，因此绝对不能输出markdown文本，否则docx文档中会出现大量未渲染md格式文本，这是不可接受的。
    2）绝对不要输出'\\n\\n'或'\n\n'（因为docx文档中一般通过行间距控制视觉舒适度，而不是多个'\\n'或'\n'来控制）。
</章节编制总体要求>

<章节编制具体要求>
{chapter_content_demand}
</章节编制具体要求>

<项目名称>
{project_name}
</项目名称>

<项目核心需求>
{project_key_demand}
</项目核心需求>

<报告完整提纲>
{project_outline}
</报告完整提纲>

<项目预期投资水平>
{project_investment}
</项目预期投资水平>

<章节模板>
{chapter_template}
</章节模板>
'''

# class legacy_调用self的call_Write_Chapter_Tool(Base_Tool):
#     tool_name = 'Write_Chapter_Tool'
#     tool_description = \
# '''控制前端Collabora CODE文档编辑器在doc/docx文档中编制章节标题和章节内容的工具。
# <支持的操作>
# "docx_write_chapter_title": 编制docx文档一个章节的标题。
# "docx_write_chapter_text": 编制docx文档一个章节的文本。
# "docx_write_chapter_table": 编制docx文档一个章节的表格。
# "docx_write_chapter_image": 编制docx文档一个章节的图片。
# </支持的操作>
#
# <注意事项>
# 1）不要连续调用"docx_write_chapter_title"输出多个标题(如2.1、2.2、2.3)然后再调用"docx_write_chapter_text"编写(如编写2.1、2.2、2.3的内容)。（因为输出是串行的，输出内容无法插入到前面。）
# </注意事项>
# '''
# #     legacy_强制required_tool_parameters = [
# #         # {
# #         #     'name': 'template_filename',
# #         #     'type': 'string',
# #         #     'description': '(用于"docx_write_chapter_text")模板文档的完整文件名，包含扩展名',
# #         #     'required': 'False',
# #         #     'default': '',
# #         # },
# #         {
# #             'name': 'operation',
# #             'type': 'string',
# #             'description': \
# #                 '''操作类型，支持以下值：
# #                 - "docx_write_chapter_title": 编制docx文档一个章节的标题。
# #                 - "docx_write_chapter_text": 编制docx文档一个章节的文本。
# #                 - "docx_write_chapter_table": 编制docx文档一个章节的表格。
# #                 - "docx_write_chapter_image": 编制docx文档一个章节的图片。
# #                 ''',
# #             'required': 'True',
# #         },
# #         {
# #             'name': 'title',
# #             'type': 'string',
# #             'description': \
# # '''
# # (用于"docx_write_chapter_title"和"docx_write_chapter_text")章节标题:
# # 1）其中章节号如"3 "、"3.2 "、"3.2.1 "、"3.2.1.1 "、"3.2.1.1.1 "、"二、"、"第二章"、"第1章"等，
# # 2）章节标题的文字不要漏写。
# # ''',
# #             'required': 'True',
# #         },
# #         {
# #             'name': 'heading',
# #             'type': 'int',
# #             'description': '(用于"docx_write_chapter_title")标题的大纲级别，如1、2、3、4、5等',
# #             'required': 'True',
# #         },
# #         {
# #             'name': 'font-size',
# #             'type': 'int',
# #             'description': '(用于"docx_write_chapter_title")标题的字体大小，如14、20等(单位为pt)',
# #             'required': 'True',
# #         },
# #         {
# #             'name': 'font-family',
# #             'type': 'string',
# #             'description': '(用于"docx_write_chapter_title")标题的字体名，如"SimSun"等',
# #             'required': 'False',
# #             'default': 'SimSun',
# #         },
# #         {
# #             'name': 'font-color',
# #             'type': 'int',
# #             'description': '(用于"docx_write_chapter_title")标题的字体颜色，仅可选择"red"、"green"、"blue"、"black"、"white"、"gray"、"yellow"之一',
# #             'required': 'False',
# #             'default': 'red',
# #         },
# #         {
# #             'name': 'font-bold',
# #             'type': 'bool',
# #             'description': '(用于"docx_write_chapter_title")标题的字体是否加粗',
# #             'required': 'False',
# #             'default': 'False',
# #         },
# #         {
# #             'name': 'center',
# #             'type': 'bool',
# #             'description': '(用于"docx_write_chapter_title")标题是否居中',
# #             'required': 'False',
# #             'default': 'False',
# #         },
# #         {
# #             'name': 'chapter_demand',
# #             'type': 'string',
# #             'description': '(用于"docx_write_chapter_text")章节文本编制的要求',
# #             'required': 'True',
# #         },
# #         {
# #             'name': 'project_name',
# #             'type': 'string',
# #             'description': '(用于"docx_write_chapter_text")项目名称',
# #             'required': 'True',
# #         },
# #         {
# #             'name': 'project_key_demand',
# #             'type': 'string',
# #             'description': '(用于"docx_write_chapter_text")项目核心需求',
# #             'required': 'True',
# #         },
# #         {
# #             'name': 'project_investment',
# #             'type': 'string',
# #             'description': '(用于"docx_write_chapter_text")项目预期投资',
# #             'required': 'True',
# #         },
# #     ]
#
#     tool_parameters = [
#         # {
#         #     'name': 'template_filename',
#         #     'type': 'string',
#         #     'description': '(用于"docx_write_chapter_text")模板文档的完整文件名，包含扩展名',
#         #     'required': 'False',
#         #     'default': '',
#         # },
#         {
#             'name': 'operation',
#             'type': 'string',
#             'description': \
#                 '''操作类型，支持以下值：
#                 - "docx_write_chapter_title": 编制docx文档一个章节的标题。
#                 - "docx_write_chapter_text": 编制docx文档一个章节的文本。
#                 - "docx_write_chapter_table": 编制docx文档一个章节的表格。
#                 - "docx_write_chapter_image": 编制docx文档一个章节的图片。
#                 ''',
#             'required': 'True',
#         },
#         {
#             'name': 'title',
#             'type': 'string',
#             'description': \
# '''
# (用于"docx_write_chapter_title"和"docx_write_chapter_text")章节标题:
# 1）其中章节号如"3 "、"3.2 "、"3.2.1 "、"3.2.1.1 "、"3.2.1.1.1 "、"二、"、"第二章"、"第1章"等，
# 2）章节标题的文字不要漏写。
# ''',
#             'required': 'False',
#         },
#         {
#             'name': 'heading',
#             'type': 'int',
#             'description': '(用于"docx_write_chapter_title")标题的大纲级别，如1、2、3、4、5等',
#             'required': 'False',
#         },
#         {
#             'name': 'font-size',
#             'type': 'int',
#             'description': '(用于"docx_write_chapter_title")标题的字体大小，如14、20等(单位为pt)',
#             'required': 'False',
#         },
#         {
#             'name': 'font-family',
#             'type': 'string',
#             'description': '(用于"docx_write_chapter_title")标题的字体名，如"SimSun"等',
#             'required': 'False',
#             'default': 'SimSun',
#         },
#         {
#             'name': 'font-color',
#             'type': 'int',
#             'description': '(用于"docx_write_chapter_title")标题的字体颜色，仅可选择"red"、"green"、"blue"、"black"、"white"、"gray"、"yellow"之一',
#             'required': 'False',
#             'default': 'red',
#         },
#         {
#             'name': 'font-bold',
#             'type': 'bool',
#             'description': '(用于"docx_write_chapter_title")标题的字体是否加粗',
#             'required': 'False',
#             'default': 'False',
#         },
#         {
#             'name': 'center',
#             'type': 'bool',
#             'description': '(用于"docx_write_chapter_title")标题是否居中',
#             'required': 'False',
#             'default': 'False',
#         },
#         {
#             'name': 'chapter_demand',
#             'type': 'string',
#             'description': '(用于"docx_write_chapter_text")章节文本编制的要求',
#             'required': 'False',
#         },
#         {
#             'name': 'project_name',
#             'type': 'string',
#             'description': '(用于"docx_write_chapter_text")项目名称',
#             'required': 'False',
#         },
#         {
#             'name': 'project_key_demand',
#             'type': 'string',
#             'description': '(用于"docx_write_chapter_text")项目核心需求',
#             'required': 'False',
#         },
#         {
#             'name': 'project_investment',
#             'type': 'string',
#             'description': '(用于"docx_write_chapter_text")项目预期投资',
#             'required': 'False',
#         },
#     ]
#
#     def __init__(self):
#         print('🔧 Write_Chapter_Tool 初始化中...')
#         # 使用通用WebSocket管理器
#         self.ws_manager = get_websocket_manager()
#         # 启动WebSocket服务器（如果尚未启动）
#
#         # -------------------------------------5112需测试CODE command, 这里port临时用5113----------------------------------------
#         # self.ws_manager.start_server(port=5113)
#         # -------------------------------------5112需测试CODE command, 这里port临时用5113----------------------------------------
#         self.ws_manager.start_server(port=config.Port.collabora_code_web_socket_server) # 5112
#         print('✅ Write_Chapter_Tool 初始化完成')
#
#     @classmethod
#     def get_tool_param_dict(cls):
#         rtn_params = Tool_Parameters(
#             properties={}
#         )
#
#         for tool_param in cls.tool_parameters:
#             name = tool_param['name']
#             required = tool_param.get('required')
#             default_value = tool_param.get('default')
#
#             type:Property_Type = ''
#             if tool_param['type'] == 'int':
#                 type = "integer"
#             elif tool_param['type'] == 'float':
#                 type = "number"
#             elif tool_param['type'] == 'bool':
#                 type = "boolean"
#             elif tool_param['type'] == 'string':
#                 type = "string"
#
#             property = Tool_Property(
#                 type=type,
#                 description=tool_param['description'] + f'(default: "{default_value}")',  # 将default_value放入description
#             )
#
#             rtn_params.properties[name] = property
#
#             if required=='True' or required==True or required=='true':
#                 rtn_params.required.append(name)
#
#         tool_param_dict = Tool_Request(
#             name = cls.tool_name,
#             description = cls.tool_description,
#             parameters = rtn_params,
#             func = cls.class_call
#         )
#
#
#         rtn_tool_param_dict = tool_param_dict.model_dump(exclude_none=True)
#         rtn_tool_param_dict['func'] = cls.class_call    # 还是手动添加Callable对象，model_dump(mode='python')似乎不行
#
#         # dred('-------------------tool_param_dict.model_dump(exclude_none=True)------------------')
#         # from pprint import pprint
#         # pprint(rtn_tool_param_dict)
#         # dred('------------------/tool_param_dict.model_dump(exclude_none=True)------------------')
#
#         return rtn_tool_param_dict
#
#     def _test_call_collabora_api(self):
#         # ------临时的websocket连接方式（选择第一个连接的客户端进行测试）------
#         timeout = 30  # 等待30秒
#         start_time = time.time()
#
#         while time.time() - start_time < timeout:
#             # 使用新的 `get_connected_clients` 方法，替换旧的 `.clients` 访问
#             registered_clients = self.ws_manager.get_connected_clients()
#
#             if registered_clients:
#                 # 选择第一个连接的客户端进行测试
#                 agent_id = registered_clients[0]
#                 print(f"✅ 成功发现已连接的客户端! Agent ID: {agent_id}")
#                 break
#             else:
#                 print("   ...尚未发现客户端，2秒后重试...")
#                 time.sleep(2)
#         # -----/临时的websocket连接方式（选择第一个连接的客户端进行测试）------
#
#         # 桥接collabora CODE接口
#         command = {
#             'type': 'office_operation',
#             'operation': 'call_python_script',
#             'agent_id': agent_id,
#             # 'agent_id': top_agent_id,
#             'data': {},
#             'timestamp': int(time.time() * 1000)
#         }
#
#         params = {
#             'text':'hi every body4!\n hi every body5!',
#             'font_name':'SimSun',
#             'font_color':'blue',
#             'font_size':12,
#         }
#         command['data'] = {
#             'cmd':'insert_text',
#             'params':params
#         }
#
#         # 通过web-socket发送至前端
#         success, message = self.ws_manager.send_command(agent_id, command)
#         return success, message
#
#     def _call_collabora_api(self, top_agent_id, cmd, params):
#         # 桥接collabora CODE接口
#         command = {
#             'type': 'office_operation',
#             'operation': 'call_python_script',
#             'agent_id': top_agent_id,
#             'data': {},
#             'timestamp': int(time.time() * 1000)
#         }
#
#         # params = {
#         #     'text':'hi every body3!',
#         #     'font_name':'SimSun',
#         #     'font_color':'blue',
#         #     'font_size':12,
#         #     'line_spacing':1.5,
#         #     'first_line_indent':700,
#         # }
#         command['data'] = {
#             'cmd':cmd,
#             'params':params
#         }
#
#         # 通过web-socket发送至前端
#         success, message = self.ws_manager.send_command(top_agent_id, command)
#         return success, message
#
#     @classmethod
#     def class_call(self, tool_call_paras: Tool_Call_Paras, **kwargs):
#         print(f'🔧 【Write_Chapter_Tool】开始调用，调用参数: {tool_call_paras.callback_tool_paras_dict}')
#
#         # 获取顶层agent_id（用于WebSocket连接管理）
#         top_agent_id = tool_call_paras.callback_top_agent_id
#         paras = tool_call_paras.callback_tool_paras_dict
#         client_ctx = tool_call_paras.callback_client_ctx
#         operation = paras.get('operation')
#
#         if not operation:
#             return Action_Result(result=safe_encode('❌ 【Write_Chapter_Tool】必须提供 "operation" 参数'))
#
#         # docx_write_chapter_title参数
#         title = paras.get('title')
#         font_name = paras.get('font-family')
#         font_color = paras.get('font-color')
#         font_bold = paras.get('font-bold')
#         font_size = paras.get('font-size')
#         outline_level = paras.get('heading')
#
#         # docx_write_chapter_text参数
#         project_name = paras.get('project_name')
#         project_key_demand = paras.get('project_key_demand')
#         project_investment = paras.get('project_investment')
#
#         # client context
#         template_filename = tool_call_paras.callback_client_ctx.custom_data_dict.get('template_filename') if (tool_call_paras.callback_client_ctx and tool_call_paras.callback_client_ctx.custom_data_dict) else None
#         shared_filename = tool_call_paras.callback_client_ctx.custom_data_dict.get('shared_filename')  if (tool_call_paras.callback_client_ctx and tool_call_paras.callback_client_ctx.custom_data_dict) else None
#
#         chapter_demand = paras.get('chapter_demand')
#
#         print(f'🎯 【Write_Chapter_Tool】Agent ID: {top_agent_id}, 全部参数: {paras}')
#         print(f'🎯 【Write_Chapter_Tool】Agent ID: {top_agent_id}, operation: {operation!r}')
#
#         try:
#             if operation == 'docx_write_chapter_title':
#                 # 校核参数
#                 if 'title' not in paras or 'heading' not in paras or 'font-size' not in paras:
#                     return Action_Result(result=safe_encode(f'❌ 【Write_Chapter_Tool】"{operation}": 操作缺少参数title、heading或font-size'))
#
#                 params = {
#                     'title': title,
#                     'outline_level': outline_level,
#                     'font_name': font_name,
#                     'font_size': font_size,
#                     'font_color': font_color,
#                     'font_bold': font_bold,
#                 }
#                 self._call_collabora_api(top_agent_id=top_agent_id, cmd='insert_title', params=params)
#                 result = f'【Write_Chapter_Tool】operation("{operation}")已经完成。'
#
#             elif operation == 'docx_write_chapter_text':
#                 # 校核参数
#                 if 'chapter_demand' not in paras:
#                     return Action_Result(result=safe_encode(f'❌ 【Write_Chapter_Tool】"{operation}": 操作缺少参数chapter_demand'))
#
#                 # 处理prompt
#                 prompt = Prompt_Write_Chapter_Text()
#
#                 prompt.chapter_content_demand = chapter_demand
#                 prompt.project_name = project_name
#                 prompt.project_key_demand = project_key_demand
#                 prompt.project_investment = project_investment
#
#                 # 读取模板文件信息
#                 if template_filename:
#                     try:
#                         template_file_path = config.Uploads.template_path + template_filename
#                         print(f'【Write_Chapter_Tool】template_file_path: {template_file_path!r}')
#
#                         # 报告完整提纲
#                         extractor = DocxOutlineExtractor()
#                         chapters = extractor.extract_outline(template_file_path, max_depth=5)
#                         prompt.project_outline = extractor.format_outline(chapters)
#
#                         print(f'【Write_Chapter_Tool】tree_string: {prompt.project_outline!r}')
#
#                         # 需编制章节的对应模板内容
#                         doc_parser = DocxParser(template_file_path)
#                         title_no = extract_chapter_no(title)
#                         prompt.chapter_template = doc_parser.get_chapter(title_no)
#                         print(f'【Write_Chapter_Tool】para_content({title_no}): {prompt.chapter_template!r}')
#                     except Exception as e:
#                         dred(f'【Write_Chapter_Tool】处理template_filename报错：{e!r}')
#
#                 # 设置后续注入文本的段落格式
#                 params = {
#                     'line_spacing': 1.5,
#                     'first_line_indent': 700,
#                     'left_margin': 0,
#                     'right_margin': 0,
#                     'space_before': 0,
#                     'space_after': 0,
#                 }
#                 self._call_collabora_api(top_agent_id=top_agent_id, cmd='set_paragraph', params=params)
#
#                 # 选择llm和参数
#                 # llm_config = config.g_online_groq_kimi_k2
#                 # llm_config = config.g_online_deepseek_chat
#                 llm_config = llm_protocol.g_online_groq_gpt_oss_120b
#                 # llm_config = llm_protocol.g_online_deepseek_chat
#                 llm = LLM_Client(llm_config=llm_config)
#
#                 # question的准备
#                 question = g_prompt_write_chapter_text.format(
#                     chapter_content_demand  = prompt.chapter_content_demand,
#                     project_name            = prompt.project_name,
#                     project_key_demand      = prompt.project_key_demand,
#                     project_outline         = prompt.project_outline,
#                     project_investment      = prompt.project_investment,
#                     chapter_template        = prompt.chapter_template,
#                 )
#
#                 dblue(f'【Write_Chapter_Tool】question: \n{question!r}')
#
#                 # llm输出
#                 query_paras = LLM_Query_Paras(
#                     query=question,
#                 )
#                 chunks = llm.ask_prepare(query_paras=query_paras).get_result_generator()
#                 print('-------------------docx_write_chapter_text-LLM-------------------')
#                 content = ''
#                 first_chunk = True
#                 for chunk in chunks:
#                     try:
#                         print(chunk, end='', flush=True)
#                         _indent = '        '
#                         # 第一个字之前增加缩进
#                         if first_chunk:
#                             # chunk = _indent + chunk
#                             first_chunk = False
#
#                         # \n后面增加缩进
#                         # chunk = chunk.replace('\n', '\n'+_indent)
#
#                         # uno_cmd = Uno_Command().uno_insert_text.format(uno_text=chunk)
#                         # self._call_raw_command(top_agent_id, uno_cmd)
#                         params = {
#                             'text': chunk,
#                             'font_name': 'SimSun',
#                             'font_color': 'black',
#                             'font_size': 12,
#                             # 'line_spacing':1.5,
#                             # 'first_line_indent':700,
#                         }
#                         self._call_collabora_api(top_agent_id=top_agent_id, cmd='insert_text', params=params)
#
#                         content += chunk
#
#                     except (ValueError, SyntaxError) as e:
#                         print(f'-----------------【Write_Chapter_Tool】"{operation}": 解析失败--------------------')
#                         print(f'报错："{e}"')
#                         print(f'chunk = "{chunk}"')
#                         print(f'content = "{content}"')
#                         print(f'----------------/【Write_Chapter_Tool】"{operation}": 解析失败--------------------')
#                         continue
#
#                 print('\n------------------/docx_write_chapter_text-LLM-------------------')
#                 content_summary = content.strip()
#                 print(f'--------content_summary:{content_summary!r}----------')
#                 content_len = len(content_summary)
#                 content_summary = f'{content_summary[:20]}...{content_summary[-20:]}' if content_len>=50 else content_summary
#                 result = f'【Write_Chapter_Tool】operation("{operation}")已经完成，写入docx内容(部分截取)为"{content_summary}"(共计{content_len}字)'
#
#             # elif operation == 'docx_write_chapter_table':
#             #     pass
#             # elif operation == 'docx_write_chapter_image':
#             #     pass
#             else:
#                 result = f'❌ 【Write_Chapter_Tool】operation "{operation}" 暂未实现或未知'
#                 return Action_Result(result=safe_encode(result))
#
#         except (ValueError, SyntaxError) as e:
#             return Action_Result(result=safe_encode(f'❌ 【Write_Chapter_Tool】"{operation}": 解析失败(报错: "{e}").'))
#         except Exception as e:
#             result = f"❌ 【Write_Chapter_Tool】'{operation}':操作失败: {e!r}"
#
#         # 确保返回安全编码的结果
#         return Action_Result(result=safe_encode(result))
#
#     def call(self, tool_call_paras:Tool_Call_Paras, **kwargs):
#         print(f'🔧 【Write_Chapter_Tool】开始调用，调用参数: {tool_call_paras.callback_tool_paras_dict}')
#
#         # 获取顶层agent_id（用于WebSocket连接管理）
#         top_agent_id = tool_call_paras.callback_top_agent_id
#         paras = tool_call_paras.callback_tool_paras_dict
#         client_ctx = tool_call_paras.callback_client_ctx
#         operation = paras.get('operation')
#
#         if not operation:
#             return Action_Result(result=safe_encode('❌ 【Write_Chapter_Tool】必须提供 "operation" 参数'))
#
#         # docx_write_chapter_title参数
#         title = paras.get('title')
#         font_name = paras.get('font-family')
#         font_color = paras.get('font-color')
#         font_bold = paras.get('font-bold')
#         font_size = paras.get('font-size')
#         outline_level = paras.get('heading')
#
#         # docx_write_chapter_text参数
#         project_name = paras.get('project_name')
#         project_key_demand = paras.get('project_key_demand')
#         project_investment = paras.get('project_investment')
#
#         # client context
#         template_filename = tool_call_paras.callback_client_ctx.custom_data_dict.get('template_filename') if (tool_call_paras.callback_client_ctx and tool_call_paras.callback_client_ctx.custom_data_dict) else None
#         shared_filename = tool_call_paras.callback_client_ctx.custom_data_dict.get('shared_filename')  if (tool_call_paras.callback_client_ctx and tool_call_paras.callback_client_ctx.custom_data_dict) else None
#
#         chapter_demand = paras.get('chapter_demand')
#
#         print(f'🎯 【Write_Chapter_Tool】Agent ID: {top_agent_id}, 全部参数: {paras}')
#         print(f'🎯 【Write_Chapter_Tool】Agent ID: {top_agent_id}, operation: {operation!r}')
#
#         try:
#             if operation == 'docx_write_chapter_title':
#                 # 校核参数
#                 if 'title' not in paras or 'heading' not in paras or 'font-size' not in paras:
#                     return Action_Result(result=safe_encode(f'❌ 【Write_Chapter_Tool】"{operation}": 操作缺少参数title、heading或font-size'))
#
#                 params = {
#                     'title': title,
#                     'outline_level': outline_level,
#                     'font_name': font_name,
#                     'font_size': font_size,
#                     'font_color': font_color,
#                     'font_bold': font_bold,
#                 }
#                 self._call_collabora_api(top_agent_id=top_agent_id, cmd='insert_title', params=params)
#                 result = f'【Write_Chapter_Tool】operation("{operation}")已经完成。'
#
#             elif operation == 'docx_write_chapter_text':
#                 # 校核参数
#                 if 'chapter_demand' not in paras:
#                     return Action_Result(result=safe_encode(f'❌ 【Write_Chapter_Tool】"{operation}": 操作缺少参数chapter_demand'))
#
#                 # 处理prompt
#                 prompt = Prompt_Write_Chapter_Text()
#
#                 prompt.chapter_content_demand = chapter_demand
#                 prompt.project_name = project_name
#                 prompt.project_key_demand = project_key_demand
#                 prompt.project_investment = project_investment
#
#                 # 读取模板文件信息
#                 if template_filename:
#                     try:
#                         template_file_path = config.Uploads.template_path + template_filename
#                         print(f'【Write_Chapter_Tool】template_file_path: {template_file_path!r}')
#
#                         # 报告完整提纲
#                         extractor = DocxOutlineExtractor()
#                         chapters = extractor.extract_outline(template_file_path, max_depth=5)
#                         prompt.project_outline = extractor.format_outline(chapters)
#
#                         print(f'【Write_Chapter_Tool】tree_string: {prompt.project_outline!r}')
#
#                         # 需编制章节的对应模板内容
#                         doc_parser = DocxParser(template_file_path)
#                         title_no = extract_chapter_no(title)
#                         prompt.chapter_template = doc_parser.get_chapter(title_no)
#                         print(f'【Write_Chapter_Tool】para_content({title_no}): {prompt.chapter_template!r}')
#                     except Exception as e:
#                         dred(f'【Write_Chapter_Tool】处理template_filename报错：{e!r}')
#
#                 # 设置后续注入文本的段落格式
#                 params = {
#                     'line_spacing': 1.5,
#                     'first_line_indent': 700,
#                     'left_margin': 0,
#                     'right_margin': 0,
#                     'space_before': 0,
#                     'space_after': 0,
#                 }
#                 self._call_collabora_api(top_agent_id=top_agent_id, cmd='set_paragraph', params=params)
#
#                 # 选择llm和参数
#                 # llm_config = config.g_online_groq_kimi_k2
#                 # llm_config = config.g_online_deepseek_chat
#                 llm_config = llm_protocol.g_online_groq_gpt_oss_120b
#                 # llm_config = llm_protocol.g_online_deepseek_chat
#                 llm = LLM_Client(llm_config=llm_config)
#
#                 # question的准备
#                 question = g_prompt_write_chapter_text.format(
#                     chapter_content_demand  = prompt.chapter_content_demand,
#                     project_name            = prompt.project_name,
#                     project_key_demand      = prompt.project_key_demand,
#                     project_outline         = prompt.project_outline,
#                     project_investment      = prompt.project_investment,
#                     chapter_template        = prompt.chapter_template,
#                 )
#
#                 dblue(f'【Write_Chapter_Tool】question: \n{question!r}')
#
#                 # llm输出
#                 query_paras = LLM_Query_Paras(
#                     query=question,
#                 )
#                 chunks = llm.ask_prepare(query_paras=query_paras).get_result_generator()
#                 print('-------------------docx_write_chapter_text-LLM-------------------')
#                 content = ''
#                 first_chunk = True
#                 for chunk in chunks:
#                     try:
#                         print(chunk, end='', flush=True)
#                         _indent = '        '
#                         # 第一个字之前增加缩进
#                         if first_chunk:
#                             # chunk = _indent + chunk
#                             first_chunk = False
#
#                         # \n后面增加缩进
#                         # chunk = chunk.replace('\n', '\n'+_indent)
#
#                         # uno_cmd = Uno_Command().uno_insert_text.format(uno_text=chunk)
#                         # self._call_raw_command(top_agent_id, uno_cmd)
#                         params = {
#                             'text': chunk,
#                             'font_name': 'SimSun',
#                             'font_color': 'black',
#                             'font_size': 12,
#                             # 'line_spacing':1.5,
#                             # 'first_line_indent':700,
#                         }
#                         self._call_collabora_api(top_agent_id=top_agent_id, cmd='insert_text', params=params)
#
#                         content += chunk
#
#                     except (ValueError, SyntaxError) as e:
#                         print(f'-----------------【Write_Chapter_Tool】"{operation}": 解析失败--------------------')
#                         print(f'报错："{e}"')
#                         print(f'chunk = "{chunk}"')
#                         print(f'content = "{content}"')
#                         print(f'----------------/【Write_Chapter_Tool】"{operation}": 解析失败--------------------')
#                         continue
#
#                 print('\n------------------/docx_write_chapter_text-LLM-------------------')
#                 content_summary = content.strip()
#                 print(f'--------content_summary:{content_summary!r}----------')
#                 content_len = len(content_summary)
#                 content_summary = f'{content_summary[:20]}...{content_summary[-20:]}' if content_len>=50 else content_summary
#                 result = f'【Write_Chapter_Tool】operation("{operation}")已经完成，写入docx内容(部分截取)为"{content_summary}"(共计{content_len}字)'
#
#             # elif operation == 'docx_write_chapter_table':
#             #     pass
#             # elif operation == 'docx_write_chapter_image':
#             #     pass
#             else:
#                 result = f'❌ 【Write_Chapter_Tool】operation "{operation}" 暂未实现或未知'
#                 return Action_Result(result=safe_encode(result))
#
#         except (ValueError, SyntaxError) as e:
#             return Action_Result(result=safe_encode(f'❌ 【Write_Chapter_Tool】"{operation}": 解析失败(报错: "{e}").'))
#         except Exception as e:
#             result = f"❌ 【Write_Chapter_Tool】'{operation}':操作失败: {e!r}"
#
#         # 确保返回安全编码的结果
#         return Action_Result(result=safe_encode(result))

class Write_Chapter_Tool(Base_Tool):
    tool_name = 'Write_Chapter_Tool'
    tool_description = \
'''控制前端Collabora CODE文档编辑器在doc/docx文档中编制章节标题和章节内容的工具。
<支持的操作>
"docx_write_chapter_title": 编制docx文档一个章节的标题。
"docx_write_chapter_text": 编制docx文档一个章节的文本。
"docx_write_chapter_table": 编制docx文档一个章节的表格。
"docx_write_chapter_image": 编制docx文档一个章节的图片。
</支持的操作>

<注意事项>
1）不要连续调用"docx_write_chapter_title"输出多个标题(如2.1、2.2、2.3)然后再调用"docx_write_chapter_text"编写(如编写2.1、2.2、2.3的内容)。（因为输出是串行的，输出内容无法插入到前面。）
</注意事项>
'''
#     legacy_强制required_tool_parameters = [
#         # {
#         #     'name': 'template_filename',
#         #     'type': 'string',
#         #     'description': '(用于"docx_write_chapter_text")模板文档的完整文件名，包含扩展名',
#         #     'required': 'False',
#         #     'default': '',
#         # },
#         {
#             'name': 'operation',
#             'type': 'string',
#             'description': \
#                 '''操作类型，支持以下值：
#                 - "docx_write_chapter_title": 编制docx文档一个章节的标题。
#                 - "docx_write_chapter_text": 编制docx文档一个章节的文本。
#                 - "docx_write_chapter_table": 编制docx文档一个章节的表格。
#                 - "docx_write_chapter_image": 编制docx文档一个章节的图片。
#                 ''',
#             'required': 'True',
#         },
#         {
#             'name': 'title',
#             'type': 'string',
#             'description': \
# '''
# (用于"docx_write_chapter_title"和"docx_write_chapter_text")章节标题:
# 1）其中章节号如"3 "、"3.2 "、"3.2.1 "、"3.2.1.1 "、"3.2.1.1.1 "、"二、"、"第二章"、"第1章"等，
# 2）章节标题的文字不要漏写。
# ''',
#             'required': 'True',
#         },
#         {
#             'name': 'heading',
#             'type': 'int',
#             'description': '(用于"docx_write_chapter_title")标题的大纲级别，如1、2、3、4、5等',
#             'required': 'True',
#         },
#         {
#             'name': 'font-size',
#             'type': 'int',
#             'description': '(用于"docx_write_chapter_title")标题的字体大小，如14、20等(单位为pt)',
#             'required': 'True',
#         },
#         {
#             'name': 'font-family',
#             'type': 'string',
#             'description': '(用于"docx_write_chapter_title")标题的字体名，如"SimSun"等',
#             'required': 'False',
#             'default': 'SimSun',
#         },
#         {
#             'name': 'font-color',
#             'type': 'int',
#             'description': '(用于"docx_write_chapter_title")标题的字体颜色，仅可选择"red"、"green"、"blue"、"black"、"white"、"gray"、"yellow"之一',
#             'required': 'False',
#             'default': 'red',
#         },
#         {
#             'name': 'font-bold',
#             'type': 'bool',
#             'description': '(用于"docx_write_chapter_title")标题的字体是否加粗',
#             'required': 'False',
#             'default': 'False',
#         },
#         {
#             'name': 'center',
#             'type': 'bool',
#             'description': '(用于"docx_write_chapter_title")标题是否居中',
#             'required': 'False',
#             'default': 'False',
#         },
#         {
#             'name': 'chapter_demand',
#             'type': 'string',
#             'description': '(用于"docx_write_chapter_text")章节文本编制的要求',
#             'required': 'True',
#         },
#         {
#             'name': 'project_name',
#             'type': 'string',
#             'description': '(用于"docx_write_chapter_text")项目名称',
#             'required': 'True',
#         },
#         {
#             'name': 'project_key_demand',
#             'type': 'string',
#             'description': '(用于"docx_write_chapter_text")项目核心需求',
#             'required': 'True',
#         },
#         {
#             'name': 'project_investment',
#             'type': 'string',
#             'description': '(用于"docx_write_chapter_text")项目预期投资',
#             'required': 'True',
#         },
#     ]

    tool_parameters = [
        # {
        #     'name': 'template_filename',
        #     'type': 'string',
        #     'description': '(用于"docx_write_chapter_text")模板文档的完整文件名，包含扩展名',
        #     'required': 'False',
        #     'default': '',
        # },
        {
            'name': 'operation',
            'type': 'string',
            'description': \
                '''操作类型，支持以下值：
                - "docx_write_chapter_title": 编制docx文档一个章节的标题。
                - "docx_write_chapter_text": 编制docx文档一个章节的文本。
                - "docx_write_chapter_table": 编制docx文档一个章节的表格。
                - "docx_write_chapter_image": 编制docx文档一个章节的图片。
                ''',
            'required': 'True',
        },
        {
            'name': 'title',
            'type': 'string',
            'description': \
'''
(用于"docx_write_chapter_title"和"docx_write_chapter_text")章节标题:
1）其中章节号如"3 "、"3.2 "、"3.2.1 "、"3.2.1.1 "、"3.2.1.1.1 "、"二、"、"第二章"、"第1章"等，
2）章节标题的文字不要漏写。
''',
            'required': 'False',
        },
        {
            'name': 'heading',
            'type': 'int',
            'description': '(用于"docx_write_chapter_title")标题的大纲级别，如1、2、3、4、5等',
            'required': 'False',
        },
        {
            'name': 'font-size',
            'type': 'int',
            'description': '(用于"docx_write_chapter_title")标题的字体大小，如14、20等(单位为pt)',
            'required': 'True',
        },
        {
            'name': 'font-family',
            'type': 'string',
            'description': '(用于"docx_write_chapter_title")标题的字体名，如"SimSun"等',
            'required': 'False',
            'default': 'SimSun',
        },
        {
            'name': 'font-color',
            'type': 'string',
            'description': '(用于"docx_write_chapter_title")标题的字体颜色，仅可选择"red"、"green"、"blue"、"black"、"white"、"gray"、"yellow"之一',
            'required': 'False',
            'default': 'red',
        },
        {
            'name': 'font-bold',
            'type': 'bool',
            'description': '(用于"docx_write_chapter_title")标题的字体是否加粗',
            'required': 'False',
            'default': 'False',
        },
        {
            'name': 'center',
            'type': 'bool',
            'description': '(用于"docx_write_chapter_title")标题是否居中',
            'required': 'False',
            'default': 'False',
        },
        {
            'name': 'chapter_demand',
            'type': 'string',
            'description': '(用于"docx_write_chapter_text")章节文本编制的要求',
            'required': 'False',
        },
        {
            'name': 'project_name',
            'type': 'string',
            'description': '(用于"docx_write_chapter_text")项目名称',
            'required': 'False',
        },
        {
            'name': 'project_key_demand',
            'type': 'string',
            'description': '(用于"docx_write_chapter_text")项目核心需求',
            'required': 'False',
        },
        {
            'name': 'project_investment',
            'type': 'string',
            'description': '(用于"docx_write_chapter_text")项目预期投资',
            'required': 'False',
        },
    ]

    _s_ws_manager = None

    def __init__(self):
        print('🔧 Write_Chapter_Tool 初始化中...')
        # 使用通用WebSocket管理器
        self.ws_manager = get_websocket_manager()
        # 启动WebSocket服务器（如果尚未启动）

        # -------------------------------------5112需测试CODE command, 这里port临时用5113----------------------------------------
        # self.ws_manager.start_server(port=5113)
        # -------------------------------------5112需测试CODE command, 这里port临时用5113----------------------------------------
        self.ws_manager.start_server(port=config.Port.collabora_code_web_socket_server) # 5112
        print(f'✅ Write_Chapter_Tool 初始化完成，port:{config.Port.collabora_code_web_socket_server}')

    @classmethod
    def init_ws_server(cls):
        if cls._s_ws_manager is None:
            cls._s_ws_manager = get_websocket_manager()

            port = config.Port.office_test_web_socket_server # ---------------------测试用5113---------------------
            # port = config.Port.collabora_code_web_socket_server # 5112
            cls._s_ws_manager.start_server(port=port)
            print(f'✅ Write_Chapter_Tool.init(cls) 初始化完成, port:{port}')

    @classmethod
    def get_tool_param_dict(cls):
        rtn_params = Tool_Parameters(
            properties={}
        )

        for tool_param in cls.tool_parameters:
            name = tool_param['name']
            required = tool_param.get('required')
            default_value = tool_param.get('default')

            type:Property_Type = ''
            if tool_param['type'] == 'int':
                type = "integer"
            elif tool_param['type'] == 'float':
                type = "number"
            elif tool_param['type'] == 'bool':
                type = "boolean"
            elif tool_param['type'] == 'string':
                type = "string"

            property = Tool_Property(
                type=type,
                description=tool_param['description'] + f'(default: {default_value})',  # 将default_value放入description
            )

            rtn_params.properties[name] = property

            if required=='True' or required==True or required=='true':
                rtn_params.required.append(name)

        tool_param_dict = Tool_Request(
            name = cls.tool_name,
            description = cls.tool_description,
            parameters = rtn_params,
            func = cls.class_call
        )


        rtn_tool_param_dict = tool_param_dict.model_dump(exclude_none=True)
        rtn_tool_param_dict['func'] = cls.class_call    # 还是手动添加Callable对象，model_dump(mode='python')似乎不行

        # dred('-------------------tool_param_dict.model_dump(exclude_none=True)------------------')
        # from pprint import pprint
        # pprint(rtn_tool_param_dict)
        # dred('------------------/tool_param_dict.model_dump(exclude_none=True)------------------')

        return rtn_tool_param_dict

    def _test_call_collabora_api(self):
        # ------临时的websocket连接方式（选择第一个连接的客户端进行测试）------
        timeout = 30  # 等待30秒
        start_time = time.time()

        while time.time() - start_time < timeout:
            # 使用新的 `get_connected_clients` 方法，替换旧的 `.clients` 访问
            registered_clients = self.ws_manager.get_connected_clients()

            if registered_clients:
                # 选择第一个连接的客户端进行测试
                agent_id = registered_clients[0]
                print(f"✅ 成功发现已连接的客户端! Agent ID: {agent_id}")
                break
            else:
                print("   ...尚未发现客户端，2秒后重试...")
                time.sleep(2)
        # -----/临时的websocket连接方式（选择第一个连接的客户端进行测试）------

        # 桥接collabora CODE接口
        command = {
            'type': 'office_operation',
            'operation': 'call_python_script',
            'agent_id': agent_id,
            # 'agent_id': top_agent_id,
            'data': {},
            'timestamp': int(time.time() * 1000)
        }

        params = {
            'text':'hi every body4!\n hi every body5!',
            'font_name':'SimSun',
            'font_color':'blue',
            'font_size':12,
        }
        command['data'] = {
            'cmd':'insert_text',
            'params':params
        }

        # 通过web-socket发送至前端
        success, message = self.ws_manager._send_office_command_test(agent_id, command)
        return success, message

    @classmethod
    def _class_call_collabora_api(cls, top_agent_id, cmd, params):
        cls.init_ws_server()

        # 桥接collabora CODE接口
        command = {
            'type': 'office_operation',
            'operation': 'call_python_script',
            'agent_id': top_agent_id,
            'data': {},
            'timestamp': int(time.time() * 1000)
        }

        # params = {
        #     'text':'hi every body3!',
        #     'font_name':'SimSun',
        #     'font_color':'blue',
        #     'font_size':12,
        #     'line_spacing':1.5,
        #     'first_line_indent':700,
        # }
        command['data'] = {
            'cmd':cmd,
            'params':params
        }

        DEBUG = True

        success = False
        message = None
        if DEBUG:
            # -----------------------DEBUG-----------------------------
            registered_clients = cls._s_ws_manager.get_connected_clients()
            if registered_clients:
                # 选择第一个连接的客户端进行测试，而不是真正对应的agent!!!
                fake_agent_id = registered_clients[0]
                success, message = cls._s_ws_manager._send_office_command_test(fake_agent_id, command)
            # ----------------------/DEBUG-----------------------------
        else:
            # 通过web-socket发送至前端
            success, message = cls._s_ws_manager._send_office_command_test(top_agent_id, command)
        return success, message

    def _call_collabora_api(self, top_agent_id, cmd, params):
        # 桥接collabora CODE接口
        command = {
            'type': 'office_operation',
            'operation': 'call_python_script',
            'agent_id': top_agent_id,
            'data': {},
            'timestamp': int(time.time() * 1000)
        }

        # params = {
        #     'text':'hi every body3!',
        #     'font_name':'SimSun',
        #     'font_color':'blue',
        #     'font_size':12,
        #     'line_spacing':1.5,
        #     'first_line_indent':700,
        # }
        command['data'] = {
            'cmd':cmd,
            'params':params
        }

        # 通过web-socket发送至前端
        success, message = self.ws_manager._send_office_command_test(top_agent_id, command)
        return success, message

    @classmethod
    def class_call(cls, tool_call_paras: Tool_Call_Paras, **kwargs):
        print(f'🔧 【Write_Chapter_Tool】开始调用，调用参数: {tool_call_paras.callback_tool_paras_dict}')

        # 获取顶层agent_id（用于WebSocket连接管理）
        top_agent_id = tool_call_paras.callback_top_agent_id
        paras = tool_call_paras.callback_tool_paras_dict
        client_ctx = tool_call_paras.callback_client_ctx
        operation = paras.get('operation')

        if not operation:
            return Agent_Tool_Result(result_summary=safe_encode('❌ 【Write_Chapter_Tool】必须提供 "operation" 参数'))

        # docx_write_chapter_title参数
        title = paras.get('title')
        font_name = paras.get('font-family')
        font_color = paras.get('font-color')
        font_bold = paras.get('font-bold')
        font_size = paras.get('font-size')
        outline_level = paras.get('heading')

        # docx_write_chapter_text参数
        project_name = paras.get('project_name')
        project_key_demand = paras.get('project_key_demand')
        project_investment = paras.get('project_investment')

        # client context
        template_filename = tool_call_paras.callback_client_ctx.custom_data_dict.get('template_filename') if (tool_call_paras.callback_client_ctx and tool_call_paras.callback_client_ctx.custom_data_dict) else None
        shared_filename = tool_call_paras.callback_client_ctx.custom_data_dict.get('shared_filename')  if (tool_call_paras.callback_client_ctx and tool_call_paras.callback_client_ctx.custom_data_dict) else None

        chapter_demand = paras.get('chapter_demand')

        print(f'🎯 【Write_Chapter_Tool】Agent ID: {top_agent_id}, 全部参数: {paras}')
        print(f'🎯 【Write_Chapter_Tool】Agent ID: {top_agent_id}, operation: {operation!r}')

        try:
            if operation == 'docx_write_chapter_title':
                # 校核参数
                if 'title' not in paras or 'heading' not in paras or 'font-size' not in paras:
                    return Agent_Tool_Result(result_summary=safe_encode(f'❌ 【Write_Chapter_Tool】"{operation}": 操作缺少参数title、heading或font-size'))

                params = {
                    'title': title,
                    'outline_level': outline_level,
                    'font_name': font_name,
                    'font_size': font_size,
                    'font_color': font_color,
                    'font_bold': font_bold,
                }
                cls._class_call_collabora_api(top_agent_id=top_agent_id, cmd='insert_title', params=params)
                result = f'【Write_Chapter_Tool】operation("{operation}")已经完成。'

            elif operation == 'docx_write_chapter_text':
                # 校核参数
                if 'chapter_demand' not in paras:
                    return Agent_Tool_Result(result_summary=safe_encode(f'❌ 【Write_Chapter_Tool】"{operation}": 操作缺少参数chapter_demand'))

                # 处理prompt
                prompt = Prompt_Write_Chapter_Text()

                prompt.chapter_content_demand = chapter_demand
                prompt.project_name = project_name
                prompt.project_key_demand = project_key_demand
                prompt.project_investment = project_investment

                # 读取模板文件信息
                if template_filename:
                    try:
                        template_file_path = config.Uploads.template_path + template_filename
                        print(f'【Write_Chapter_Tool】template_file_path: {template_file_path!r}')

                        # 报告完整提纲
                        extractor = DocxOutlineExtractor()
                        chapters = extractor.extract_outline(template_file_path, max_depth=5)
                        prompt.project_outline = extractor.format_outline(chapters)

                        print(f'【Write_Chapter_Tool】tree_string: {prompt.project_outline!r}')

                        # 需编制章节的对应模板内容
                        doc_parser = DocxParser(template_file_path)
                        title_no = extract_chapter_no(title)
                        prompt.chapter_template = doc_parser.get_chapter(title_no)
                        print(f'【Write_Chapter_Tool】para_content({title_no}): {prompt.chapter_template!r}')
                    except Exception as e:
                        dred(f'【Write_Chapter_Tool】处理template_filename报错：{e!r}')

                # 设置后续注入文本的段落格式
                params = {
                    'line_spacing': 1.5,
                    'first_line_indent': 700,
                    'left_margin': 0,
                    'right_margin': 0,
                    'space_before': 0,
                    'space_after': 0,
                }
                cls._class_call_collabora_api(top_agent_id=top_agent_id, cmd='set_paragraph', params=params)

                # 选择llm和参数
                # llm_config = llm_protocol.g_online_groq_kimi_k2
                llm_config = llm_protocol.g_online_deepseek_chat
                # llm_config = llm_protocol.g_local_gpt_oss_120b_mxfp4_lmstudio
                # llm_config = llm_protocol.g_online_groq_gpt_oss_120b
                # llm_config = llm_protocol.g_online_deepseek_chat
                llm = LLM_Client(llm_config=llm_config)

                # question的准备
                question = g_prompt_write_chapter_text.format(
                    chapter_content_demand  = prompt.chapter_content_demand,
                    project_name            = prompt.project_name,
                    project_key_demand      = prompt.project_key_demand,
                    project_outline         = prompt.project_outline,
                    project_investment      = prompt.project_investment,
                    chapter_template        = prompt.chapter_template,
                )

                dblue(f'【Write_Chapter_Tool】question: \n{question!r}')

                # llm输出
                query_paras = LLM_Query_Paras(
                    query=question,
                )
                chunks = llm.ask_prepare(query_paras=query_paras).get_result_generator()
                print('-------------------docx_write_chapter_text-LLM-------------------')
                content = ''
                first_chunk = True
                for chunk in chunks:
                    try:
                        print(chunk, end='', flush=True)
                        _indent = '        '
                        # 第一个字之前增加缩进
                        if first_chunk:
                            # chunk = _indent + chunk
                            first_chunk = False

                        # \n后面增加缩进
                        # chunk = chunk.replace('\n', '\n'+_indent)

                        # uno_cmd = Uno_Command().uno_insert_text.format(uno_text=chunk)
                        # self._call_raw_command(top_agent_id, uno_cmd)
                        params = {
                            'text': chunk,
                            'font_name': 'SimSun',
                            'font_color': 'black',
                            'font_size': 12,
                            # 'line_spacing':1.5,
                            # 'first_line_indent':700,
                        }
                        cls._class_call_collabora_api(top_agent_id=top_agent_id, cmd='insert_text', params=params)

                        content += chunk

                    except (ValueError, SyntaxError) as e:
                        print(f'-----------------【Write_Chapter_Tool】"{operation}": 解析失败--------------------')
                        print(f'报错："{e}"')
                        print(f'chunk = "{chunk}"')
                        print(f'content = "{content}"')
                        print(f'----------------/【Write_Chapter_Tool】"{operation}": 解析失败--------------------')
                        continue

                print('\n------------------/docx_write_chapter_text-LLM-------------------')
                content_summary = content.strip()
                print(f'--------content_summary:{content_summary!r}----------')
                content_len = len(content_summary)
                content_summary = f'{content_summary[:20]}...{content_summary[-20:]}' if content_len>=50 else content_summary
                result = f'【Write_Chapter_Tool】operation("{operation}")已经完成，写入docx内容(部分截取)为"{content_summary}"(共计{content_len}字)'

            # elif operation == 'docx_write_chapter_table':
            #     pass
            # elif operation == 'docx_write_chapter_image':
            #     pass
            else:
                result = f'❌ 【Write_Chapter_Tool】operation "{operation}" 暂未实现或未知'
                return Agent_Tool_Result(result_summary=safe_encode(result))

        except (ValueError, SyntaxError) as e:
            return Agent_Tool_Result(result_summary=safe_encode(f'❌ 【Write_Chapter_Tool】"{operation}": 解析失败(报错: "{e}").'))
        except Exception as e:
            err(e)
            result = f"❌ 【Write_Chapter_Tool】'{operation}':操作失败: {e!r}"

        # 确保返回安全编码的结果
        return Agent_Tool_Result(result_summary=safe_encode(result))

    def call(self, tool_call_paras:Tool_Call_Paras, **kwargs):
        print(f'🔧 【Write_Chapter_Tool】开始调用，调用参数: {tool_call_paras.callback_tool_paras_dict}')

        # 获取顶层agent_id（用于WebSocket连接管理）
        top_agent_id = tool_call_paras.callback_top_agent_id
        paras = tool_call_paras.callback_tool_paras_dict
        client_ctx = tool_call_paras.callback_client_ctx
        operation = paras.get('operation')

        if not operation:
            return Agent_Tool_Result(result_summary=safe_encode('❌ 【Write_Chapter_Tool】必须提供 "operation" 参数'))

        # docx_write_chapter_title参数
        title = paras.get('title')
        font_name = paras.get('font-family')
        font_color = paras.get('font-color')
        font_bold = paras.get('font-bold')
        font_size = paras.get('font-size')
        outline_level = paras.get('heading')

        # docx_write_chapter_text参数
        project_name = paras.get('project_name')
        project_key_demand = paras.get('project_key_demand')
        project_investment = paras.get('project_investment')

        # client context
        template_filename = tool_call_paras.callback_client_ctx.custom_data_dict.get('template_filename') if (tool_call_paras.callback_client_ctx and tool_call_paras.callback_client_ctx.custom_data_dict) else None
        shared_filename = tool_call_paras.callback_client_ctx.custom_data_dict.get('shared_filename')  if (tool_call_paras.callback_client_ctx and tool_call_paras.callback_client_ctx.custom_data_dict) else None

        chapter_demand = paras.get('chapter_demand')

        print(f'🎯 【Write_Chapter_Tool】Agent ID: {top_agent_id}, 全部参数: {paras}')
        print(f'🎯 【Write_Chapter_Tool】Agent ID: {top_agent_id}, operation: {operation!r}')

        try:
            if operation == 'docx_write_chapter_title':
                # 校核参数
                if 'title' not in paras or 'heading' not in paras or 'font-size' not in paras:
                    return Agent_Tool_Result(result_summary=safe_encode(f'❌ 【Write_Chapter_Tool】"{operation}": 操作缺少参数title、heading或font-size'))

                params = {
                    'title': title,
                    'outline_level': outline_level,
                    'font_name': font_name,
                    'font_size': font_size,
                    'font_color': font_color,
                    'font_bold': font_bold,
                }
                self._call_collabora_api(top_agent_id=top_agent_id, cmd='insert_title', params=params)
                result = f'【Write_Chapter_Tool】operation("{operation}")已经完成。'

            elif operation == 'docx_write_chapter_text':
                # 校核参数
                if 'chapter_demand' not in paras:
                    return Agent_Tool_Result(result_summary=safe_encode(f'❌ 【Write_Chapter_Tool】"{operation}": 操作缺少参数chapter_demand'))

                # 处理prompt
                prompt = Prompt_Write_Chapter_Text()

                prompt.chapter_content_demand = chapter_demand
                prompt.project_name = project_name
                prompt.project_key_demand = project_key_demand
                prompt.project_investment = project_investment

                # 读取模板文件信息
                if template_filename:
                    try:
                        template_file_path = config.Uploads.template_path + template_filename
                        print(f'【Write_Chapter_Tool】template_file_path: {template_file_path!r}')

                        # 报告完整提纲
                        extractor = DocxOutlineExtractor()
                        chapters = extractor.extract_outline(template_file_path, max_depth=5)
                        prompt.project_outline = extractor.format_outline(chapters)

                        print(f'【Write_Chapter_Tool】tree_string: {prompt.project_outline!r}')

                        # 需编制章节的对应模板内容
                        doc_parser = DocxParser(template_file_path)
                        title_no = extract_chapter_no(title)
                        prompt.chapter_template = doc_parser.get_chapter(title_no)
                        print(f'【Write_Chapter_Tool】para_content({title_no}): {prompt.chapter_template!r}')
                    except Exception as e:
                        dred(f'【Write_Chapter_Tool】处理template_filename报错：{e!r}')

                # 设置后续注入文本的段落格式
                params = {
                    'line_spacing': 1.5,
                    'first_line_indent': 700,
                    'left_margin': 0,
                    'right_margin': 0,
                    'space_before': 0,
                    'space_after': 0,
                }
                self._call_collabora_api(top_agent_id=top_agent_id, cmd='set_paragraph', params=params)

                # 选择llm和参数
                # llm_config = llm_protocol.g_online_groq_kimi_k2
                llm_config = llm_protocol.g_online_deepseek_chat
                # llm_config = llm_protocol.g_online_groq_gpt_oss_120b
                # llm_config = llm_protocol.g_online_deepseek_chat
                llm = LLM_Client(llm_config=llm_config)

                # question的准备
                question = g_prompt_write_chapter_text.format(
                    chapter_content_demand  = prompt.chapter_content_demand,
                    project_name            = prompt.project_name,
                    project_key_demand      = prompt.project_key_demand,
                    project_outline         = prompt.project_outline,
                    project_investment      = prompt.project_investment,
                    chapter_template        = prompt.chapter_template,
                )

                dblue(f'【Write_Chapter_Tool】question: \n{question!r}')

                # llm输出
                query_paras = LLM_Query_Paras(
                    query=question,
                )
                chunks = llm.ask_prepare(query_paras=query_paras).get_result_generator()
                print('-------------------docx_write_chapter_text-LLM-------------------')
                content = ''
                first_chunk = True
                for chunk in chunks:
                    try:
                        print(chunk, end='', flush=True)
                        _indent = '        '
                        # 第一个字之前增加缩进
                        if first_chunk:
                            # chunk = _indent + chunk
                            first_chunk = False

                        # \n后面增加缩进
                        # chunk = chunk.replace('\n', '\n'+_indent)

                        # uno_cmd = Uno_Command().uno_insert_text.format(uno_text=chunk)
                        # self._call_raw_command(top_agent_id, uno_cmd)
                        params = {
                            'text': chunk,
                            'font_name': 'SimSun',
                            'font_color': 'black',
                            'font_size': 12,
                            # 'line_spacing':1.5,
                            # 'first_line_indent':700,
                        }
                        self._call_collabora_api(top_agent_id=top_agent_id, cmd='insert_text', params=params)

                        content += chunk

                    except (ValueError, SyntaxError) as e:
                        print(f'-----------------【Write_Chapter_Tool】"{operation}": 解析失败--------------------')
                        print(f'报错："{e}"')
                        print(f'chunk = "{chunk}"')
                        print(f'content = "{content}"')
                        print(f'----------------/【Write_Chapter_Tool】"{operation}": 解析失败--------------------')
                        continue

                print('\n------------------/docx_write_chapter_text-LLM-------------------')
                content_summary = content.strip()
                print(f'--------content_summary:{content_summary!r}----------')
                content_len = len(content_summary)
                content_summary = f'{content_summary[:20]}...{content_summary[-20:]}' if content_len>=50 else content_summary
                result = f'【Write_Chapter_Tool】operation("{operation}")已经完成，写入docx内容(部分截取)为"{content_summary}"(共计{content_len}字)'

            # elif operation == 'docx_write_chapter_table':
            #     pass
            # elif operation == 'docx_write_chapter_image':
            #     pass
            else:
                result = f'❌ 【Write_Chapter_Tool】operation "{operation}" 暂未实现或未知'
                return Agent_Tool_Result(result_summary=safe_encode(result))

        except (ValueError, SyntaxError) as e:
            return Agent_Tool_Result(result_summary=safe_encode(f'❌ 【Write_Chapter_Tool】"{operation}": 解析失败(报错: "{e}").'))
        except Exception as e:
            err(e)
            result = f"❌ 【Write_Chapter_Tool】'{operation}':操作失败: {e!r}"

        # 确保返回安全编码的结果
        return Agent_Tool_Result(result_summary=safe_encode(result))

ws_server = Web_Socket_Server_Manager.start_server(config.Port.office_test_web_socket_server)
class Insert_Math_Formula_Tool(Base_Tool):
    tool_name= 'Insert_Math_Formula_Tool'
    tool_description='''
在文档中插入libre-office的StarMath格式的数学公式的工具。要注意StarMath格式和LaTeX格式不同，以下是LaTeX转为StarMath格式的简要说明：
\int_{a}^{b} g(x)\,dx → int from a to b g(x) dx
\frac{A}{B} → {A} over {B}
\sqrt{X} → sqrt {X}
\sum_{i=1}^{n} → sum from i = 1 to n
\cdot → cdot
\alpha,\beta,\gamma → alpha, beta, gamma（去掉反斜杠）
^, _ 指数/下标语法相同：x^2, x^{ab}, x_{0}
'''
    tool_parameters={
        'type':'object',
        'properties':{
            'formula': {'type': 'string', 'description': '公式字符串，如“E = m c^2”'},
            'as_inline': {'type': 'bool', 'description': '是否inline'},
            'base_font_height': {'type': 'int', 'description': '公式基本字体高度'},
        },
        'required': ['formula'],
        'additionalProperties': False,
    }

    def __init__(self):
        pass

    @classmethod
    def class_call(cls, tool_call_paras:Tool_Call_Paras, **kwargs):
        from web_socket_server import  Web_Socket_Server
        from threading import Thread
        from uuid import uuid4

        paras = tool_call_paras.callback_tool_paras_dict
        print('------------------paras--------------------')
        print(paras)
        print('-----------------/paras--------------------')
        formula = paras.get('formula')
        as_inline = paras.get('as_inline')
        base_font_height = paras.get('base_font_height')

        # ws_server = Web_Socket_Server_Manager.start_server(5113)
        def _test():
            print('------------------_test_call_collabora_api--------------------')
            while True:
                if ws_server.connections:
                    break

                time.sleep(0.1)

            if ws_server.connections:
                command = {
                    'type': 'office_operation',
                    'operation': 'call_python_script',
                    'data': {},
                    'timestamp': int(time.time() * 1000)
                }
                params = {
                    'formula': formula,
                    'as_inline': as_inline,
                    'base_font_height': base_font_height,
                }
                command['data'] = {
                    'cmd': 'insert_math',
                    'params': params
                }
                # 通过web-socket发送至前端
                success, message = _send_office_command_test(ws_server, command)
                print(f'command={command!r}')
                print(f'success={success!r}, message={message!r}')
                print('-----------------/_test_call_collabora_api--------------------')

                # ws_server.web_socket.close()   # 可能是 ws.close() / ws.shutdown() / await ws.close()
                return success, message

        thread = Thread(target=_test)
        thread.start()

        # ws_server.start_server()

        thread.join()

        action_result = Agent_Tool_Result(
            result_summary=f'formula: {formula!r}已经成功插入文档。',
            result_resource_id=str(uuid4()),
            # resource_data=resource_data
        )

        return action_result

    def call(self, tool_call_paras:Tool_Call_Paras, **kwargs):
        return Insert_Math_Formula_Tool.class_call(tool_call_paras=tool_call_paras, **kwargs)

# import re
# def latex_to_starmath(s: str) -> str:
#     rules = [
#         (r'\\int\s*_\{([^}]*)\}\s*\^\{([^}]*)\}', r'int from \1 to \2'),
#         (r'\\sum\s*_\{([^}]*)\}\s*\^\{([^}]*)\}', r'sum from \1 to \2'),
#         (r'\\prod\s*_\{([^}]*)\}\s*\^\{([^}]*)\}', r'prod from \1 to \2'),
#         (r'\\sqrt\{([^}]*)\}', r'sqrt {\1}'),
#         (r'\\frac\{([^}]*)\}\{([^}]*)\}', r'{\1} over {\2}'),
#         (r'\\cdot', 'cdot'),
#         (r'\\,|\\;|\\:|\\!', ' '),
#         # 常见希腊字母
#         (r'\\alpha','alpha'), (r'\\beta','beta'), (r'\\gamma','gamma'),
#         (r'\\Delta','Delta'), (r'\\delta','delta'),
#         # ……需要再补就继续加
#     ]
#     for pat, rep in rules:
#         s = re.sub(pat, rep, s)
#     return s
#
# def insert_math_mixed(input_formula: str, **opts):
#     # 先简单判别是否像 LaTeX（包含 \int 或 \frac 等），是的话转一下
#     maybe_latex = any(tok in input_formula for tok in ['\\int','\\frac','\\sqrt','\\sum','\\prod','\\cdot','\\alpha','\\beta','\\gamma'])
#     formula = latex_to_starmath(input_formula) if maybe_latex else input_formula
#     return InsertMath(formula=formula, **opts)  # 复用你已有的 InsertMath





#     # def call(self, tool_call_paras:Tool_Call_Paras, **kwargs):
#     # # def call(self,
#     # #          callback_tool_paras_dict,
#     # #          callback_agent_config,
#     # #          callback_agent_id,
#     # #          callback_last_tool_ctx,
#     # #          callback_father_agent_exp,
#     # #          ):
#     #     dgreen(f'tool_paras_dict: "{tool_call_paras.callback_tool_paras_dict}"')
#     #     dir = tool_call_paras.callback_tool_paras_dict['path']
#     #
#     #     try:
#     #         # 调用工具
#     #         # files_str = get_folder_files_info_string(directory=dir, mode='name')
#     #         items_str = safe_encode(get_folder_all_items_string(directory=dir))
#     #         # files_str = get_folder_files_info_string(directory=dir, mode='basename')
#     #     except Exception as e:
#     #         items_str = f'报错: {e!r}'
#     #
#     #     # 调用工具后，结果作为action_result返回
#     #     action_result = Agent_Tool_Result(result=items_str)
#     #     # action_result = items_str
#     #     return action_result

# class Office_Tool(Base_Tool):
#     name = 'Office_Tool'
#     description = \
# '''控制前端Collabora CODE文档编辑器对文档进行编制的工具。
# 支持的操作包括：
# - "docx_write_chapter_title": 编制docx文档一个章节的标题。
# - "docx_write_chapter_text": 编制docx文档一个章节的文本。
# - "docx_write_chapter_table": 编制docx文档一个章节的表格。
# - "docx_write_chapter_image": 编制docx文档一个章节的图片。
# '''
#     parameters = [
#         {
#             'name': 'operation',
#             'type': 'string',
#             'description': \
# '''操作类型，支持以下值：
# - "docx_write_chapter_title": 编制docx文档一个章节的标题。
# - "docx_write_chapter_text": 编制docx文档一个章节的文本。
# - "docx_write_chapter_table": 编制docx文档一个章节的表格。
# - "docx_write_chapter_image": 编制docx文档一个章节的图片。
# ''',
#             'required': 'True',
#         },
#         {
#             'name': 'title',
#             'type': 'string',
#             'description': '(用于"docx_write_chapter_title")章节号，如"3 "、"3.2 "、"3.2.1 "、"3.2.1.1 "、"3.2.1.1.1 "、"二、"、"第二章"、"第1章"等',
#             'required': 'True',
#         },
#         {
#             'name': 'heading',
#             'type': 'int',
#             'description': '(用于"docx_write_chapter_title")标题的大纲级别，如1、2、3、4、5等',
#             'required': 'True',
#         },
#         {
#             'name': 'font-size',
#             'type': 'int',
#             'description': '(用于"docx_write_chapter_title")标题的字体大小，如14、20等(单位为pt)',
#             'required': 'True',
#         },
#         {
#             'name': 'font-family',
#             'type': 'string',
#             'description': '(用于"docx_write_chapter_title")标题的字体名，如"SimSun"等',
#             'required': 'False',
#             'default': 'SimSun',
#         },
#         {
#             'name': 'font-color',
#             'type': 'int',
#             'description': '(用于"docx_write_chapter_title")标题的字体颜色，仅可选择"red"、"green"、"blue"、"black"、"white"、"gray"、"yellow"之一',
#             'required': 'False',
#             'default': 'red',
#         },
#         {
#             'name': 'font-bold',
#             'type': 'bool',
#             'description': '(用于"docx_write_chapter_title")标题的字体是否加粗',
#             'required': 'False',
#             'default': 'False',
#         },
#         {
#             'name': 'center',
#             'type': 'bool',
#             'description': '(用于"docx_write_chapter_title")标题是否居中',
#             'required': 'False',
#             'default': 'False',
#         },
#         {
#             'name': 'chapter_demand',
#             'type': 'string',
#             'description': '(用于"docx_write_chapter_text")章节文本编制的要求',
#             'required': 'True',
#         },
#     ]
#
#     def __init__(self):
#         print('🔧 Office_Tool 初始化中...')
#         # 使用通用WebSocket管理器
#         # self.ws_manager = get_websocket_manager()
#         # 启动WebSocket服务器（如果尚未启动）
#
#         # -------------------------------------5112需测试CODE command, 这里port临时用5113----------------------------------------
#         # self.ws_manager.start_server(port=5113)
#         # -------------------------------------5112需测试CODE command, 这里port临时用5113----------------------------------------
#         # self.ws_manager.start_server(port=config.Port.collabora_code_web_socket_server) # 5112
#         print('✅ Office_Tool 初始化完成')
#
#     def _call_raw_command(self, top_agent_id, uno_cmd):
#         # 桥接collabora CODE接口
#         command = {
#             'type': 'office_operation',
#             'operation': 'call_raw_command',
#             'agent_id': top_agent_id,
#             'data': {},
#             'timestamp': int(time.time() * 1000)
#         }
#
#         # UNO指令
#         # 解决\n问题
#         uno_cmd = uno_cmd.replace('\n', '\\n')
#
#         # string->obj
#         cmd_obj = json5.loads(uno_cmd)
#
#         # 获取uno指令
#         command['data'] = cmd_obj
#         cmd_name = cmd_obj['Values']['Command']
#
#         # 通过web-socket发送至前端
#         success, message = self.ws_manager.send_command(top_agent_id, command)
#         return success, message
#
#     def call(self, tool_call_paras: Tool_Call_Paras):
#         print(f'🔧 【Office_Tool】开始调用，调用参数: {tool_call_paras.callback_tool_paras_dict}')
#
#         # 获取顶层agent_id（用于WebSocket连接管理）
#         top_agent_id = tool_call_paras.callback_top_agent_id
#         paras = tool_call_paras.callback_tool_paras_dict
#         operation = paras.get('operation')
#
#         # docx_write_chapter_title参数
#         title = paras.get('title')
#         uno_font = paras.get('font-family')
#         uno_char_color = paras.get('font-color')
#         uno_bold = paras.get('font-bold')
#         uno_outline_level = paras.get('heading')
#
#         # docx_write_chapter_text参数
#         chapter_demand = paras.get('chapter_demand')
#
#         if not operation:
#             return Action_Result(result=safe_encode('❌ 【Office_Tool】必须提供 "operation" 参数'))
#
#         print(f'🎯 【Office_Tool】Agent ID: {top_agent_id}, 全部参数: {paras}')
#         print(f'🎯 【Office_Tool】Agent ID: {top_agent_id}, operation: {operation!r}')
#
#         try:
#
#
#             # 根据操作类型填充data
#             if operation == 'docx_write_chapter_title':
#                 # 校核参数
#                 if 'title' not in paras or 'heading' not in paras or 'font-size' not in paras:
#                     return Action_Result(result=safe_encode(f'❌ 【Office_Tool】"{operation}": 操作缺少参数title、heading或font-size'))
#
#                 # 标题设置字体
#                 if uno_font:
#                     uno_cmd = Uno_Command().uno_font.format(uno_font=uno_font)
#                     print(f'-------------------uno_font:{uno_cmd!r}-----------------')
#                     self._call_raw_command(top_agent_id, uno_cmd)
#
#                 # 标题设置颜色
#                 if uno_char_color:
#                     uno_cmd = Uno_Command().uno_char_color.format(uno_char_color=Uno_Color[uno_char_color])
#                     print(f'-------------------uno_char_color:{uno_cmd!r}-----------------')
#                     self._call_raw_command(top_agent_id, uno_cmd)
#
#                 # 标题设置粗体
#                 if uno_bold:
#                     uno_cmd = Uno_Command().uno_bold
#                     print(f'-------------------uno_bold:{uno_cmd!r}-----------------')
#                     self._call_raw_command(top_agent_id, uno_cmd)
#
#                 # 标题设置大纲级别
#                 if uno_outline_level:
#                     uno_cmd = Uno_Command().uno_outline_level.format(uno_outline_level=uno_outline_level)
#                     print(f'-------------------uno_outline_level:{uno_cmd!r}-----------------')
#                     self._call_raw_command(top_agent_id, uno_cmd)
#
#                 # 标题文字
#                 uno_cmd = Uno_Command().uno_insert_text_and_return.format(uno_text=title)
#                 print(f'-------------------uno_insert_text_and_return:{uno_cmd!r}-----------------')
#                 self._call_raw_command(top_agent_id, uno_cmd)
#                 result = f'【Office_Tool】operation("{operation}")已经完成。'
#
#             elif operation == 'docx_write_chapter_text':
#                 # 校核参数
#                 if 'chapter_demand' not in paras:
#                     return Action_Result(result=safe_encode(f'❌ 【Office_Tool】"{operation}": 操作缺少参数chapter_demand'))
#
#
#                 # 选择llm和参数
#                 llm_config = config.g_online_deepseek_chat
#                 llm = LLM_Client(llm_config=llm_config)
#
#                 # llm输出
#                 question = chapter_demand + '\n注意：不能输出markdown格式和风格的内容，因为你的输出要写入docx文档。'
#                 chunks = llm.ask_prepare(question=question).get_result_generator()
#                 print('-------------------docx_write_chapter_text-LLM-------------------')
#                 content = ''
#                 first_chunk = True
#                 for chunk in chunks:
#                     try:
#                         print(chunk, end='', flush=True)
#                         _indent = '        '
#                         # 第一个字之前增加缩进
#                         if first_chunk:
#                             chunk = _indent + chunk
#                             first_chunk = False
#
#                         # \n后面增加缩进
#                         chunk = chunk.replace('\n', '\n'+_indent)
#
#                         uno_cmd = Uno_Command().uno_insert_text.format(uno_text=chunk)
#                         self._call_raw_command(top_agent_id, uno_cmd)
#                         content += chunk
#                     except (ValueError, SyntaxError) as e:
#                         print(f'-----------------【Office_Tool】"{operation}": Uno_Command解析失败--------------------')
#                         print(f'报错："{e}"')
#                         print(f'uno_cmd = "{Uno_Command().uno_insert_text}"')
#                         print(f'chunk = "{chunk}"')
#                         print(f'content = "{content}"')
#                         print(f'----------------/【Office_Tool】"{operation}": Uno_Command解析失败--------------------')
#                         continue
#                 print('\n------------------/docx_write_chapter_text-LLM-------------------')
#                 content_summary = content.strip()
#                 print(f'--------content_summary:{content_summary!r}----------')
#                 content_len = len(content_summary)
#                 content_summary = f'{content_summary[:20]}...{content_summary[-20:]}' if content_len>=50 else content_summary
#                 result = f'【Office_Tool】operation("{operation}")已经完成，写入docx内容(部分截取)为"{content_summary}"(共计{content_len}字)'
#
#             elif operation == 'docx_write_chapter_table':
#                 pass
#             elif operation == 'docx_write_chapter_image':
#                 pass
#             else:
#                 result = f'❌ 【Office_Tool】operation "{operation}" 暂未实现或未知'
#                 return Action_Result(result=safe_encode(result))
#
#         except (ValueError, SyntaxError) as e:
#             # print(f"❌ 错误：解析字典失败: {e}。")
#             return Action_Result(result=safe_encode(f'❌ 【Office_Tool】"{operation}": Uno_Command解析失败(报错: "{e}").'))
#         except Exception as e:
#             result = f"❌ 【Office_Tool】'{operation}':操作失败: {e!r}"
#
#         # 确保返回安全编码的结果
#         return Action_Result(result=safe_encode(result))

# 用于测试的主函数
def main_office():
    import config
    from agent.core.react_agent import Tool_Agent
    from agent.core.agent_config import Agent_Config

    tools = [Office_Tool]
    query = '请在文档中插入一段测试文本："这是通过 Agent 系统插入的测试内容。"'

    config = Agent_Config(
        base_url='http://powerai.cc:28001/v1',  # llama-4-400b
        api_key='empty',
    )

    agent = Tool_Agent(
        query=query,
        tool_classes=tools,
        agent_config=config
    )
    agent.init()
    success = agent.run()

def main_write_chapter_tool_test():
    tool = Write_Chapter_Tool()
    tool._test_call_collabora_api()

def main_only_call_test():
    paras = {
        'formula': 'E = m cdot c^{2} int from a to b f(x) dx = F(b) - F(a)',
        'as_inline': True,
        'base_font_height': 12,
    }

    tool_call_paras = Tool_Call_Paras(
        callback_tool_paras_dict = paras,
        callback_agent_config=Agent_Config(),
        callback_top_agent_id='',
        callback_agent_id='',
        callback_father_agent_exp=''
    )
    Insert_Math_Formula_Tool.class_call(tool_call_paras)

if __name__ == "__main__":
    # main_office()
    # main_write_chapter_tool_test()
    # main_only_call_test()
    # main_only_call_test()
    _test_call_collabora_api(ws_server)