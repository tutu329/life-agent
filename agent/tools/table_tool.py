import win32com.client as win32
from win32com.client import constants
import os
import re

from server_manager.web_server_task_manager import Web_Client_Data, Web_Client_Data_Type, Web_Client_Table_Data
from agent.base_tool import Base_Tool
from utils.extract import extract_dict_string
from utils.folder import get_folder_files_info_string
import json5
import json

from config import dred, dgreen, dblue, dcyan, dyellow
from dataclasses import dataclass, asdict

def _draw_table_on_web_page(table_data):
    dred(f'_draw_table_on_web_page() starts to draw table on web page...')
    pass

def extract_table_to_word(
        excel_path,
        sheet_name,
        table_title='',
        is_vertical=True,
        draw_table='true',
        is_web_server=True,
) -> str:
    """
    从指定的 Excel 文件和工作表中提取表格数据，并将其以文本形式复制到 Word 中，
    根据每个单元格的 NumberFormat 格式化数值，包括百分数格式。

    :param excel_path: Excel 文件的路径
    :param sheet_name: 工作表的名称
    :param table_title: 表的标题
    """
    # 检查文件是否存在
    if not os.path.exists(excel_path):
        print(f"错误: Excel 文件 '{excel_path}' 不存在。")
        return

    # 初始化 Excel 应用
    try:
        # -------这两行可以解决开web server环境下调用excel的报错---------
        # 报错：-2147221008, 尚未调用 CoInitialize
        import pythoncom
        pythoncom.CoInitialize()
        # ---------------------------------------------------------

        excel = win32.gencache.EnsureDispatch('Excel.Application')
        excel.Visible = False  # 设置为 True 以调试
        excel.DisplayAlerts = False
    except Exception as e:
        print(f"无法启动 Excel 应用程序: {e}")
        return

    try:
        # 打开指定的工作簿
        workbook = excel.Workbooks.Open(os.path.abspath(excel_path))

        # 获取指定的工作表
        try:
            sheet = workbook.Worksheets(sheet_name)
        except Exception as e:
            print(f"无法找到工作表 '{sheet_name}': {e}")
            workbook.Close(SaveChanges=False)
            excel.Quit()
            return

        # 确定表格的起始和结束单元格
        used_range = sheet.UsedRange
        start_row = used_range.Row
        start_col = used_range.Column
        end_row = start_row + used_range.Rows.Count - 1
        end_col = start_col + used_range.Columns.Count - 1

        # 提取数据
        data = []
        for row in range(start_row, end_row + 1):
            row_data = []
            for col in range(start_col, end_col + 1):
                cell_obj = sheet.Cells(row, col)
                cell_value = cell_obj.Value
                if cell_value is None:
                    cell_str = ""
                elif isinstance(cell_value, (int, float)):
                    # 获取单元格的数字格式
                    number_format = cell_obj.NumberFormat
                    decimal_places, is_percentage = get_decimal_places_and_percentage(number_format)
                    if is_percentage:
                        # 将数值转换为百分比
                        cell_percentage = cell_value * 100
                        cell_str = f"{cell_percentage:.{decimal_places}f}%"
                    else:
                        # 格式化数值，保留相应的小数位数
                        cell_str = f"{cell_value:.{decimal_places}f}"
                else:
                    cell_str = str(cell_value)
                row_data.append(cell_str)

            # [row_data的string, row_data]
            data.append(["\t".join(row_data), row_data])

        # 将数据转换为单一的文本字符串，每行以换行符分隔
        table_text = "\n".join([item[0] for item in data])

    except Exception as e:
        print(f"在处理 Excel 文件时出错: {e}")
        workbook.Close(SaveChanges=False)
        excel.Quit()
        return

    finally:
        # 关闭工作簿和 Excel 应用
        workbook.Close(SaveChanges=False)
        excel.Quit()

        if draw_table=='false' or draw_table=='False' or draw_table==False:
            return table_text

        if is_web_server:
            _draw_table_on_web_page(table_data=data)
            return table_text

        # 获取当前光标位置
        word = win32.gencache.EnsureDispatch('Word.Application')
        selection = word.Selection

        # 获取表格的行数和列数
        num_rows = len(data)
        num_cols = len(data[0][1])
        # num_cols = len(data[0]) if num_rows > 0 else 0

        if num_rows == 0 or num_cols == 0:
            print("警告: 提取到的表格数据为空。")
            return

        if not is_vertical:
            # Step 1: 在当前位置插入分节符（下一页）
            selection.InsertBreak(constants.wdSectionBreakNextPage)

        # Step 2.1: 添加表头
        selection.TypeText(f'{table_title}')
        # 存储当前对齐方式
        previous_alignment = selection.ParagraphFormat.Alignment
        # 设置段落居中对齐
        selection.ParagraphFormat.Alignment = win32.constants.wdAlignParagraphCenter

        # Step 2.2: 添加表格
        table = selection.Tables.Add(Range=selection.Range, NumRows=num_rows, NumColumns=num_cols)

        if not is_vertical:
            # 设置当前节的页面方向为横向
            selection.Sections(1).PageSetup.Orientation = constants.wdOrientLandscape

        # Step 3: 在表格后插入另一个分节符（下一页）
        # 将光标移动到表格之后
        selection.SetRange(Start=table.Range.End, End=table.Range.End)

        if not is_vertical:
            # 插入分节符
            selection.InsertBreak(constants.wdSectionBreakNextPage)
            # 设置新节的页面方向为纵向
            selection.Sections(1).PageSetup.Orientation = constants.wdOrientPortrait

        # 填充表格数据
        try:
            for i in range(num_rows):
                for j in range(num_cols):
                    cell = table.Cell(i + 1, j + 1)
                    cell.Range.Text = data[i][1][j]
        except Exception as e:
            print(f'表格创建出错: {e}')

        # 设置表格边框
        set_table_borders(table)

        # 设置整个表格的字体大小为 10.5 (五号字体)
        table.Range.Font.Size = 10.5

        # 自动调整表格以适应内容
        # Behavior 参数可以是以下值之一：
        # 0 或 win32com.client.constants.wdAutoFitFixed：固定列宽，不自动调整。
        # 1 或 win32com.client.constants.wdAutoFitContent：根据内容自动调整列宽。
        # 2 或 win32com.client.constants.wdAutoFitWindow：自动调整表格宽度以适应窗口（页面）宽度。
        table.AutoFitBehavior(2)  # Behavior = 2

        if not is_vertical:
            # 使用GoTo将光标移到下一段落(表格之后)
            selection.GoTo(What=constants.wdGoToLine, Which=constants.wdGoToNext)

        # 设置段落居中对齐
        selection.ParagraphFormat.Alignment = previous_alignment

    return table_text

def set_table_borders(table):
    """
    设置 Word 表格的边框样式：外边框为粗线，内部分隔线为细线。

    :param table: Word 表格对象
    """
    # 获取 Word 常量
    constants = win32.constants

    # 设置内部边框为细线
    table.Borders(constants.wdBorderHorizontal).LineStyle = constants.wdLineStyleSingle
    table.Borders(constants.wdBorderHorizontal).LineWidth = constants.wdLineWidth025pt  # 细线

    table.Borders(constants.wdBorderVertical).LineStyle = constants.wdLineStyleSingle
    table.Borders(constants.wdBorderVertical).LineWidth = constants.wdLineWidth025pt  # 细线

    # 设置外边框为粗线
    table.Borders(constants.wdBorderTop).LineStyle = constants.wdLineStyleSingle
    table.Borders(constants.wdBorderTop).LineWidth = constants.wdLineWidth150pt  # 粗线

    table.Borders(constants.wdBorderBottom).LineStyle = constants.wdLineStyleSingle
    table.Borders(constants.wdBorderBottom).LineWidth = constants.wdLineWidth150pt  # 粗线

    table.Borders(constants.wdBorderLeft).LineStyle = constants.wdLineStyleSingle
    table.Borders(constants.wdBorderLeft).LineWidth = constants.wdLineWidth150pt  # 粗线

    table.Borders(constants.wdBorderRight).LineStyle = constants.wdLineStyleSingle
    table.Borders(constants.wdBorderRight).LineWidth = constants.wdLineWidth150pt  # 粗线

def get_decimal_places_and_percentage(number_format):
    """
    根据 Excel 单元格的 NumberFormat 获取小数位数和是否为百分比格式。

    :param number_format: Excel 单元格的 NumberFormat 属性
    :return: (小数位数（整数）, 是否为百分比（布尔值）)
    """
    is_percentage = False
    # 检查是否包含百分号
    if '%' in number_format:
        is_percentage = True

    # 使用正则表达式查找小数点后的零的数量
    # 例如：0.00, #,##0.000, 0.00%, #,##0.000%
    match = re.search(r'0\.([0]+)', number_format)
    if match:
        decimal_places = len(match.group(1))
    else:
        # 如果没有明确的小数位数，则默认返回0
        decimal_places = 0

    return decimal_places, is_percentage

class Table_Tool(Base_Tool):
    name='Table_Tool'
    description=\
'''从excel文件中获取表格数据。
'''
    parameters=[
        {
            'name': 'excel_path',
            'type': 'string',
            'description': \
'''
本参数为Excel文件的路径
''',
            'required': 'True',
        },
        {
            'name': 'sheet_name',
            'type': 'string',
            'description': \
'''
本参数为Excel文件中工作表的名称
''',
            'required': 'True',
        },
        {
            'name': 'table_title',
            'type': 'string',
            'description': \
'''
本参数为表格数据返回后绘制时用的表格标题
''',
            'required': 'True',
        },
        {
            'name': 'is_vertical',
            'type': 'bool',
            'description': \
'''
本参数为表格数据返回后是否垂直绘制，填写"true"或"false"
''',
            'required': 'True',
        },
        {
            'name': 'draw_table',
            'type': 'bool',
            'description': \
                '''
                本参数为表格数据返回后是否绘制表格，填写"true"或"false"
                ''',
            'required': 'True',
        },
    ]
    def __init__(self):
        pass

    def call(self,
             callback_tool_paras_dict,
             callback_agent_config,
             # in_is_web_server=True,
             # in_client_data_sse_stream_buf=None,
             ):
        dred('-----------------Table_Tool.call() invoked.---------------------')
        dred('------table_tool paras-------')
        dred(callback_tool_paras_dict)
        dred('-----/table_tool paras-------')
        # dict_string = extract_dict_string(in_thoughts)
        # dict = json5.loads(dict_string)
        # excel_path = dict['tool_parameters']['excel_path']
        # sheet_name = dict['tool_parameters']['sheet_name']
        # table_title = dict['tool_parameters']['table_title']
        # is_vertical = dict['tool_parameters']['is_vertical']
        # draw_table = dict['tool_parameters']['draw_table']
        excel_path = callback_tool_paras_dict['excel_path']
        sheet_name = callback_tool_paras_dict['sheet_name']
        table_title = callback_tool_paras_dict['table_title']
        is_vertical = callback_tool_paras_dict['is_vertical']
        draw_table = callback_tool_paras_dict['draw_table']
        dyellow(f'draw_table: {draw_table!r}')

        # 读取xls数据，并在word里绘制(仅在local调用word时)
        table_text = extract_table_to_word(
            excel_path=excel_path,
            sheet_name=sheet_name,
            table_title=table_title,
            is_vertical=is_vertical,
            draw_table=draw_table,
            is_web_server=callback_agent_config.is_web_server,
        )

        dred(f'-----------------draw_table({draw_table!r})--------------')
        dred(f'-----------------agent_config.is_web_server({callback_agent_config.is_web_server!r})--------------')
        dred(f'-----------------agent_config.stream_tool_client_data({callback_agent_config.web_server_stream_tool_client_data!r})--------------')
        if (draw_table=='true' or draw_table=='True') and callback_agent_config.is_web_server and self.tool_client_data_stream_buf:
            table_data = Web_Client_Table_Data(content=table_text, caption=sheet_name)
            client_data = Web_Client_Data(type=Web_Client_Data_Type.TABLE, data=table_data)
            client_data_str = json.dumps(asdict(client_data), ensure_ascii=False)
            # json5会导致传到client为JavaScript的对象字面量({type: "table", data: {content: "...", caption: "..."}})
            # 而不是json格式({"type": "table", "data": {"content": "...", "caption": "..."}})
            # client_data_str = json5.dumps(asdict(client_data)).encode('utf-8').decode('unicode_escape')
            dred(f'-----------------client data_str---------------\n{client_data_str}')
            dred(f'-----------------------------------------------\n')
            callback_agent_config.web_server_stream_tool_client_data(client_data_str)

        # 调用工具后，结果作为action_result返回
        action_result = table_text
        dred('-----------------Table_Tool.call() result:---------------------')
        dred(action_result)
        return action_result

def main_word():
    # excel_file = 'd:/demo/负荷及平衡.xlsx'        # Excel 文件路径
    excel_file = 'y:/demo/负荷及平衡.xlsx'        # Excel 文件路径
    sheet = '负荷预测'                          # 工作表名称
    word_file = 'output.docx'                   # 输出的 Word 文件路径（可选）

    print(extract_table_to_word(excel_file, sheet, table_title='负荷预测表', word_path=word_file ))

def main_client():
    import config
    from agent.tool_agent import Tool_Agent
    from agent.agent_config import Config

    tools=[Table_Tool]
    # tools=[Folder_Tool, Search_Tool]
    # query = '第一步：搜索"万向创新聚能城"，返回万向创新聚能城所在城市；第二步搜索所在城市，返回该城市概况'
    query=''
    print(f'os: "{config.get_os()}"')
    if config.get_os()=='windows':
        query = r'请返回y:/demo/负荷及平衡.xlsx里的"负荷预测"标签中的表格数据，不绘制表格'
        # query = r'请返回d:/demo/负荷及平衡.xlsx里的"负荷预测"标签中的表格数据.'
    else:
        query = r'请告诉我y:/demo/负荷及平衡.xlsx里的"负荷预测"标签中的表格数据.'

    config = Config(
        base_url='http://powerai.cc:28001/v1',  # llama-4-400b#llama-4-400b
        # base_url='http://powerai.cc:38001/v1',   #deepseek-r1-671b
        api_key='empty',
    )
    agent = Tool_Agent(
        query=query,
        tool_classes=tools,
        agent_config=config,
    )
    agent.init()
    success = agent.run()

# 使用示例
if __name__ == "__main__":
    main_client()