# VBA中调用本文件的方式
# Dim shell As Object
# Set shell = VBA.CreateObject("WScript.Shell")
# ' 定义命令字符串
# Dim command As String
# command = "cmd.exe /c y: && cd y:\life-agent && python -m client.office.office_client"
#
# ' 执行命令
# ‘ 1为控制台可见，2为控制台在后台，0为控制台不可见
# shell.Run command, 1, True
import config
# 目前报告自动编制.docm中的运行宏的快捷键定义为"Ctrl+9"

import json
from dataclasses import asdict

from singleton import singleton

import win32com.client as win32
# import win32com
from dataclasses import dataclass

from tools.llm.api_client import LLM_Client
from client.office.parse_scheme import get_scheme_list

from agent.core.tool_agent import Tool_Agent
from agent.tools.folder_tool import Folder_Tool
from agent.tools.search_tool import Search_Tool
from agent.tools.table_tool import Table_Tool

from config import dred, dblue, dyellow
from server_manager.legacy_web_server_base import legacy_Web_Server_Base
from server_manager.web_server_task_manager import Web_Client_Data_Type, Web_Client_Data, Web_Client_Text_Data


@singleton
class Office_Client():
    def __init__(self, base_url=config.LLM_Default.url, temperature=0.7, api_key='empty'):
        self.llm = None
        self.url = base_url
        self.api_key = api_key
        self.temperature = temperature
        self.word = None
        self.status_ok = False

        self._init()

    def _init(self):
        try:
            self.llm = LLM_Client(
                url=self.url,
                api_key=self.api_key,
                temperature=self.temperature,
            )
            # 启动Word应用程序
            self.word = win32.gencache.EnsureDispatch('Word.Application')
            dyellow(f'已获取word对象.')
            # 启动Excel应用程序
            self.excel = win32.gencache.EnsureDispatch('Excel.Application')
            dyellow(f'已获取excel对象.')

            self._get_word_selection()
        except AttributeError as e:
            dred(f'Office_Client报错, "{e}"。可能需要尝试删除%TEMP%\gen_py文件夹以解决该问题。')
            dred(f'当前程序已推出。')
            exit()
        except TypeError as e:
            dred(f'可能是word文件或excel文件未打开，报错: "{e}"')


    def _excel_get_selected_table(self):
        wb = self.excel.ActiveWorkbook
        ws = wb.ActiveSheet
        selection = self.excel.Selection
        # 获取选中的单元格范围
        data = []
        for row in selection:
            row_data = []
            for cell in row:
                row_data.append(cell.Value)
            data.append(row_data)
        return data

    def excel_get_selected_table_string(self):
        # 获取Excel中的表格数据
        table_data = self._excel_get_selected_table()

        # 将表格数据格式化为字符串
        table_str = '\n'.join(['\t'.join(map(str, row)) for row in table_data])
        return table_str

    def word_get_selected_text(self):
        if self._word_status_wrong():
            return

        # doc = self.word.ActiveDocument
        selection = self.word.Selection
        selected_text = selection.Text
        return selected_text

    def word_update_selected_text(self, new_text):
        if self._word_status_wrong():
            return

        selection = self.word.Selection
        selection.Text = new_text

    def _get_word_selection(self):
        selection = self.word.Selection
        if selection is None:
            dred(f'word.Selection为None，可能存在已打开但无文档的word窗口，请关闭该窗口.')
            # raise ValueError("word.Selection为None，可能存在已打开但无文档的word窗口，请关闭该窗口.")
            self.status_ok = False
        self.status_ok = True

    def _word_status_wrong(self):
        return not self.status_ok

    def word_insert_image_at_cursor(self, image_path):
        if image_path =='' or self._word_status_wrong():
            return

        selection = self.word.Selection

        # 插入图片
        selection.InlineShapes.AddPicture(
            FileName=image_path,
            LinkToFile=False,  # 设置为 True 如果你希望图片链接到文件，而不是嵌入
            SaveWithDocument=True  # 设置为 True 以便将图片保存到文档中
        )

        # 可选：调整图片大小（例如，宽度为 300 点，高度按比例调整）
        inline_shape = selection.InlineShapes(1)  # 获取刚插入的图片
        inline_shape.LockAspectRatio = True
        inline_shape.Width = 300  # 设置宽度为300点

        selection.TypeParagraph()  # 插入段落符，继续后续操作

    def word_insert_heading_at_cursor(self, heading, style='标题 1'):
        if heading=='' or style=='' or self._word_status_wrong():
            return

        # dred(f'word: "{self.word}"')
        # dred(f'word.Selection: "{self.word.Selection}"')
        selection = self.word.Selection

        selection.Style = style         # 使用Word的内置样式名称（中文版本）
        selection.TypeText(heading)     # 如：'一、概述'
        selection.TypeParagraph()       # 插入段落符

    def word_insert_text_at_cursor(self, text, style='！正文'):
        if text == '' or style == '' or self._word_status_wrong():
            return

        selection = self.word.Selection
        selection.Style = style
        selection.TypeText(text)
        selection.TypeParagraph()

    def word_insert_text_at_cursor_without_end(self, text, style='！正文'):
        if text == '' or style == '' or self._word_status_wrong():
            return

        selection = self.word.Selection
        selection.Style = style
        selection.TypeText(text)

    def word_insert_text_end_at_cursor(self):
        if self._word_status_wrong():
            return

        selection = self.word.Selection
        selection.TypeParagraph()

    def word_insert_llm_stream_at_cursor(self, prompt):
        if self._word_status_wrong():
            return

        try:
            # 可选：使Word应用程序可见，便于调试
            self.word.Visible = True

            # 获取当前的选区
            selection = self.word.Selection

            # 插入 '正文’ ，样式为正文
            selection.Style = '！正文'

            # 在光标位置插入新文本
            gen = self.llm.ask_prepare(question=prompt).get_answer_generator()
            for chunk in gen:
                selection.TypeText(chunk)
            selection.TypeParagraph()

            # 可选：保存文档或执行其他操作
            # word.ActiveDocument.Save()

            # 可选：关闭Word应用程序
            # word.Quit()
        except Exception as e:
            print(f'word通信报错: "{e}"')

@dataclass
class Chapter_Info:
    heading_num: str = ''       # 如'1.2.1
    heading_style: str = ''     # 如'标题 3'
    heading: str = ''           # 如'建设必要性'
    prompt: str = ''            # 如'网络搜索“xxx”，并编写xxx情况...'
    type: str = ''              # 如'chapter'或'alone_text'

def _get_chapter_info(scheme_item) -> Chapter_Info:
    if scheme_item.get('type') and scheme_item.get('type') == 'chapter':
        # 返回章节标题和content内容
        content = scheme_item['content']
        heading_num = content['heading_num']

        # 获取标题level对应的样式style，如'标题 3'
        level = len(heading_num.strip().split('.'))
        heading_style = f'标题 {level}'

        chapter_info = Chapter_Info(
            heading_num=heading_num,
            heading_style=heading_style,
            heading=f'{heading_num} {content["heading"]}',
            prompt=content['text'],
            type='chapter'
        )
        return chapter_info
    elif scheme_item.get('type') and scheme_item.get('type') == 'along_text':
        # 返回along_text的content内容
        content = scheme_item['content']
        chapter_info = Chapter_Info(
            prompt=content['text'],
            type = 'alone_text'
        )
        return chapter_info
    else:
        # 返回空内容
        return Chapter_Info()

# 初始化和调用agent
def _ask_agent(
        prompt,
        output_stream_buf=dyellow,
        output_stream_end_func=None,
        thinking_stream_buf=None,
        log_stream_buf=None,
        tool_client_data_stream_buf=None,
        base_url=config.LLM_Default.url,
        model_id='',
        temperature=0.7,
        api_key='empty'
) -> str:
    tools = [Folder_Tool, Search_Tool, Table_Tool]
    agent = Tool_Agent(
        query=prompt,
        tool_classes=tools,
        stream_result=output_stream_buf,     # 最终输出 -> dyellow
        stream_thinking=thinking_stream_buf,
        stream_log=log_stream_buf,
        in_output_end=output_stream_end_func,
        in_base_url=base_url,
        in_api_key=api_key,
        in_model_id=model_id,
        in_temperature=temperature
    )
    dblue(f'tools registered: {agent.registered_tool_instances_dict}')

    agent.init()
    agent.set_stream_tool_result_data(tool_result_data_output_func=tool_client_data_stream_buf)
    success = agent.run()

    result = ''

    if success:
        dblue(f"\n[运行结果]大语言模型agent执行成功。")
        result = agent.get_final_answer()
        dblue(result)
    else:
        dred(f"\n[运行结果]大语言模型agent执行失败，请进一步优化指令。")
        result = '大语言模型agent执行失败，请进一步优化指令。'
        dred(result)

    return result

class Web_Office_Write(legacy_Web_Server_Base):
    def __init__(self,
                 scheme_file_path,
                 base_url=config.LLM_Default.url,
                 api_key=config.LLM_Default.api_key,
                 model_id='',
                 temperature=config.LLM_Default.temperature
                 ):
        self.scheme_file_path = scheme_file_path
        self.base_url = base_url
        self.api_key = api_key
        self.model_id = model_id
        self.temperature = temperature
        self.output_stream_buf = None
        self.thinking_stream_buf = None
        self.log_stream_buf = None
        self.tool_client_data_stream_buf = None

    def init(self) -> None:
        pass


    def insert_heading_at_cursor(self, heading, style='标题 1'):
        if heading.startswith('0 '):
            text_data = Web_Client_Text_Data(
                content=heading[2:],
                alignment='center',
                is_heading='true',
                font='黑体, SimHei',
                size='22',
                color='red'
            )
            client_data = Web_Client_Data(type=Web_Client_Data_Type.TEXT, data=text_data)
            client_data_str = json.dumps(asdict(client_data), ensure_ascii=False)
            self.output_stream_buf(client_data_str)

            # text_data = Web_Client_Text_Data(
            #     content='\n',
            #     is_heading='true',
            #     font='黑体, SimHei',
            #     size='22',
            #     color='red'
            # )
            # client_data = Web_Client_Data(type=Web_Client_Data_Type.TEXT, data=text_data)
            # client_data_str = json.dumps(asdict(client_data), ensure_ascii=False)
            # self.output_stream_buf(client_data_str)

            # self.output_stream_buf(heading[2:])
            # self.output_stream_buf('\n')
        else:
            text_data = Web_Client_Text_Data(
                content=heading,
                is_heading='true',
                font='宋体, SimSun',
                size='12',
                color='red'
            )
            client_data = Web_Client_Data(type=Web_Client_Data_Type.TEXT, data=text_data)
            client_data_str = json.dumps(asdict(client_data), ensure_ascii=False)
            self.output_stream_buf(client_data_str)

            # text_data = Web_Client_Text_Data(
            #     content='\n',
            #     is_heading='true',
            #     font='宋体, SimSun',
            #     size='12',
            #     color='red'
            # )
            # client_data = Web_Client_Data(type=Web_Client_Data_Type.TEXT, data=text_data)
            # client_data_str = json.dumps(asdict(client_data), ensure_ascii=False)
            # self.output_stream_buf(client_data_str)

            # self.output_stream_buf(heading)
            # self.output_stream_buf('\n')

    def insert_text_at_cursor_without_end(self, text, style='！正文'):
        text_data = Web_Client_Text_Data(
            content=text,
            font='宋体, SimSun',
            size='12',
            color='black'
        )
        client_data = Web_Client_Data(type=Web_Client_Data_Type.TEXT, data=text_data)
        client_data_str = json.dumps(asdict(client_data), ensure_ascii=False)
        self.output_stream_buf(client_data_str)

        # self.output_stream_buf(text)

    def insert_text_end_at_cursor(self):
        text_data = Web_Client_Text_Data(
            content='\n',
            font='宋体, SimSun',
            size='12',
            color='black'
        )
        client_data = Web_Client_Data(type=Web_Client_Data_Type.TEXT, data=text_data)
        client_data_str = json.dumps(asdict(client_data), ensure_ascii=False)
        self.output_stream_buf(client_data_str)


        # self.output_stream_buf('\n')
        # self.output_stream_buf('\n')

    def run(self) -> None:
        # 读取报告编制指令
        scheme_list = get_scheme_list(self.scheme_file_path)
        dyellow(f'报告提纲({self.scheme_file_path})读取完毕.')

        # 初始化office自动化工具
        # office = Office_Client(
        #     base_url=base_url,
        #     api_key=api_key,
        #     temperature=temperature,
        # )
        # dyellow(f'已获取office对象.')

        # 编制报告
        for item in scheme_list:
            chapter_info = _get_chapter_info(item)
            if chapter_info.type == 'chapter':
                dblue(f'chapter_info: "{chapter_info}"')
                # 编写标题
                self.insert_heading_at_cursor(heading=chapter_info.heading, style=chapter_info.heading_style)
                if chapter_info.prompt != '':
                    # 编写正文
                    prompt = chapter_info.prompt
                    result = _ask_agent(
                        prompt,
                        output_stream_buf=self.insert_text_at_cursor_without_end,
                        thinking_stream_buf=self.thinking_stream_buf,
                        log_stream_buf=self.log_stream_buf,
                        tool_client_data_stream_buf=self.tool_client_data_stream_buf,
                        output_stream_end_func=self.insert_text_end_at_cursor,
                        base_url=self.base_url,
                        api_key=self.api_key,
                        model_id=self.model_id,
                        temperature=self.temperature
                    )
                    # office.word_insert_text_at_cursor(text=result)
            elif chapter_info.type == 'alone_text':
                if chapter_info.prompt != '':
                    # 编写正文
                    prompt = chapter_info.prompt
                    result = _ask_agent(
                        prompt,
                        output_stream_buf=self.insert_text_at_cursor_without_end,
                        thinking_stream_buf=self.thinking_stream_buf,
                        log_stream_buf=self.log_stream_buf,
                        tool_client_data_stream_buf=self.tool_client_data_stream_buf,
                        output_stream_end_func=self.insert_text_end_at_cursor,
                        base_url=self.base_url,
                        api_key=self.api_key,
                        model_id=self.model_id,
                        temperature=self.temperature
                    )

        # office.word_insert_heading_at_cursor('一、概要', '标题 1')
        # office.word_insert_heading_at_cursor('1、现状', '标题 2')
        # office.word_insert_llm_stream_at_cursor('我叫土土')

    def set_stream_result(self, result_output_func):
        self.output_stream_buf = result_output_func

    def set_stream_thinking(self, thinking_output_func):
        self.thinking_stream_buf = thinking_output_func

    def set_stream_log(self, log_output_func):
        self.log_stream_buf = log_output_func

    def set_stream_tool_result_data(self, tool_result_data_output_func):
        self.tool_client_data_stream_buf = tool_result_data_output_func

# 电厂接入系统报告的编制
def report_on_plant_grid_connection_system(scheme_file_path, base_url=config.LLM_Default.url, api_key=config.LLM_Default.api_key, temperature=config.LLM_Default.temperature):
    # 读取报告编制指令
    scheme_list = get_scheme_list(scheme_file_path)
    dyellow(f'报告提纲读取完毕.')

    # 初始化office自动化工具
    office = Office_Client(
        base_url=base_url,
        api_key=api_key,
        temperature=temperature,
    )
    # dyellow(f'已获取office对象.')

    # 编制报告
    for item in scheme_list:
        chapter_info = _get_chapter_info(item)
        if chapter_info.type=='chapter':
            dblue(f'chapter_info: "{chapter_info}"')
            # 编写标题
            office.word_insert_heading_at_cursor(heading=chapter_info.heading, style=chapter_info.heading_style)
            if chapter_info.prompt!='':
                # 编写正文
                prompt = chapter_info.prompt
                result = _ask_agent(
                    prompt,
                    output_stream_buf = office.word_insert_text_at_cursor_without_end,
                    output_stream_end_func = office.word_insert_text_end_at_cursor,
                    base_url=office.url,
                    api_key=office.api_key,
                    temperature=office.temperature
                )
                # office.word_insert_text_at_cursor(text=result)
        elif chapter_info.type=='alone_text':
            if chapter_info.prompt!='':
                # 编写正文
                prompt = chapter_info.prompt
                result = _ask_agent(
                    prompt,
                    output_stream_buf = office.word_insert_text_at_cursor_without_end,
                    output_stream_end_func = office.word_insert_text_end_at_cursor,
                    base_url=office.url,
                    api_key=office.api_key,
                    temperature=office.temperature
                )

    # office.word_insert_heading_at_cursor('一、概要', '标题 1')
    # office.word_insert_heading_at_cursor('1、现状', '标题 2')
    # office.word_insert_llm_stream_at_cursor('我叫土土')

def main():
    report_on_plant_grid_connection_system(
        'D:/server/life-agent/client/office/xiaoshan_prj/scheme.txt',
        base_url=config.LLM_Default.url,
        api_key=config.LLM_Default.api_key,
        temperature=config.LLM_Default.temperature,
        # temperature=0,
    )
    # report_on_plant_grid_connection_system('d:/demo/scheme.txt')
    input('【结束】')


def agent_tool_test():
    tools=[Folder_Tool, Search_Tool, Table_Tool]
    # query = '告诉我"D:\\ComfyUI\\models\\checkpoints"下有哪些文件'
    query = '请返回"d:/demo/负荷及平衡.xlsx"的"负荷预测"标签里的表格给我'
    # query = '告诉我"y:\\demo\\依据"下有哪些文件'
    agent = Tool_Agent(query=query, tool_classes=tools)
    print(f'tools registered: {agent.registered_tool_instances_dict}')
    agent.init()
    success = agent.run()
    if success:
        dblue(f"\n[运行结果]成功。")
    else:
        dred(f"\n[运行结果]失败，请进一步优化问题的描述。")
    print(f'最终答复:')
    print(agent.get_final_answer())

def server_main():
    Web_Office_Write

if __name__ == "__main__":
    # main()
    server_main()
    # agent_tool_test()