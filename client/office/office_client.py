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


from singleton import singleton

import win32com.client as win32
# import win32com
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from tools.llm.api_client import LLM_Client
from client.office.parse_scheme import get_scheme_list

from agent.tool_agent import Tool_Agent
from agent.tools.folder_tool import Folder_Tool
from agent.tools.search_tool import Search_Tool
from agent.tools.table_tool import Table_Tool

from config import dred, dgreen, dblue, dcyan, dyellow

@singleton
class Office_Client():
    def __init__(self):
        self.llm = None
        self.word = None
        self.status_ok = False

        self._init()

    def _init(self):
        self.llm = LLM_Client()
        # 启动Word应用程序
        self.word = win32.gencache.EnsureDispatch('Word.Application')
        # 启动Excel应用程序
        self.excel = win32.gencache.EnsureDispatch('Excel.Application')

        self._get_word_selection()

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

def _get_chapter_info(scheme_item) -> Chapter_Info:
    if scheme_item.get('type') and scheme_item.get('type') == 'chapter':
        content = scheme_item['content']
        heading_num = content['heading_num']

        # 获取标题level对应的样式style，如'标题 3'
        level = len(heading_num.strip().split('.'))
        heading_style = f'标题 {level}'

        chapter_info = Chapter_Info(
            heading_num=heading_num,
            heading_style=heading_style,
            heading=f'{heading_num} {content["heading"]}',
            prompt=content['text']
        )
        return chapter_info
    else:
        return Chapter_Info()

# 初始化和调用agent
def _ask_agent(
        prompt,
        output_stream_buf=dyellow,
        output_stream_end_func=None,
) -> str:
    tools = [Folder_Tool, Search_Tool, Table_Tool]
    agent = Tool_Agent(
        in_query=prompt,
        in_tool_classes=tools,
        in_output_stream_buf=output_stream_buf,     # 最终输出 -> dyellow
        in_output_end=output_stream_end_func,
    )
    dblue(f'tools registered: {agent.registered_tool_instances_dict}')

    agent.init()
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

# 电厂接入系统报告的编制
def report_on_plant_grid_connection_system():
    # 读取报告编制指令
    scheme_list = get_scheme_list('scheme.txt')

    # 初始化office自动化工具
    office = Office_Client()

    # 编制报告
    for item in scheme_list:
        chapter_info = _get_chapter_info(item)
        dblue(f'chapter_info: "{chapter_info}"')
        # 编写标题
        office.word_insert_heading_at_cursor(heading=chapter_info.heading, style=chapter_info.heading_style)
        if chapter_info.prompt!='':
            # 编写正文
            prompt = chapter_info.prompt
            result = _ask_agent(
                prompt,
                output_stream_buf = office.word_insert_text_at_cursor_without_end,
                output_stream_end_func = office.word_insert_text_end_at_cursor
            )
            # office.word_insert_text_at_cursor(text=result)

    # office.word_insert_heading_at_cursor('一、概要', '标题 1')
    # office.word_insert_heading_at_cursor('1、现状', '标题 2')
    # office.word_insert_llm_stream_at_cursor('我叫土土')

def main():
    report_on_plant_grid_connection_system()
    input('【结束】')


def agent_tool_test():
    tools=[Folder_Tool, Search_Tool, Table_Tool]
    # query = '告诉我"D:\\ComfyUI\\models\\checkpoints"下有哪些文件'
    query = '请返回"d:/demo/负荷及平衡.xlsx"的"负荷预测"标签里的表格给我'
    # query = '告诉我"y:\\demo\\依据"下有哪些文件'
    agent = Tool_Agent(in_query=query, in_tool_classes=tools)
    print(f'tools registered: {agent.registered_tool_instances_dict}')
    agent.init()
    success = agent.run()
    if success:
        dblue(f"\n[运行结果]成功。")
    else:
        dred(f"\n[运行结果]失败，请进一步优化问题的描述。")
    print(f'最终答复:')
    print(agent.get_final_answer())

if __name__ == "__main__":
    main()
    # agent_tool_test()