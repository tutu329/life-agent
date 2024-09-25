# VBA中调用本文件的方式
# Dim shell As Object
# Set shell = VBA.CreateObject("WScript.Shell")
# ' 定义命令字符串
# Dim command As String
# command = "cmd.exe /c y: && cd y:\life-agent && python -m client.office_client"
#
# ' 执行命令
# ‘ 1为控制台可见，2为控制台在后台，0为控制台不可见
# shell.Run command, 1, True


from singleton import singleton

import win32com.client as win32
# import win32com
import requests
import json

from tools.llm.api_client import LLM_Client

@singleton
class Office_Client():
    def __init__(self):
        self.llm = None
        self.word = None

        self._init()

    def _init(self):
        self.llm = LLM_Client()
        # 启动Word应用程序
        self.word = win32.gencache.EnsureDispatch('Word.Application')
        # 启动Excel应用程序
        self.excel = win32.gencache.EnsureDispatch('Excel.Application')

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
        doc = self.word.ActiveDocument
        selection = self.word.Selection
        selected_text = selection.Text
        return selected_text

    def word_update_selected_text(self, new_text):
        selection = self.word.Selection
        selection.Text = new_text

    def word_insert_heading_at_cursor(self, heading, style='标题 1'):
        selection = self.word.Selection

        selection.Style = style         # 使用Word的内置样式名称（中文版本）
        selection.TypeText(heading)     # 如：'一、概述'
        selection.TypeParagraph()       # 插入段落符

    def word_insert_llm_stream_at_cursor(self, prompt):
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

def report_on_plant_grid_connection_system():
    office = Office_Client()
    office.word_insert_heading_at_cursor('一、概要', '标题 1')
    office.word_insert_heading_at_cursor('1、现状', '标题 2')
    office.word_insert_llm_stream_at_cursor('我叫土土')

def main():
    report_on_plant_grid_connection_system()
    input('【结束】')

if __name__ == "__main__":
    main()
