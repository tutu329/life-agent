from agent.tools.base_tool import Base_Tool
from utils.extract import legacy_extract_dict_string
import json5

from config import Global


class Energy_Investment_Plan_Tool(Base_Tool):
    tool_name= 'Energy_Investment_Plan_Tool'
    tool_description= '''
通过"能源投资优化系统"对风光储等能源设施进行基于线性规划的最优投资规模计算的工具.
所输入参数必须遵循如下要求, 否则转换为dict数据时会失败:
1)绝对不能增加如#开头的注释.
2)bool变量必须为true或false, 而不能是True或False.
'''
    tool_parameters=[
        {
            'name': 'rate',
            'type': 'float',
            'description': '基准收益率',
            'required': 'True',
        },
        {
            'name': 'simu_years',
            'type': 'int',
            'description': '仿真年数(年)',
            'required': 'True',
        },
        {
            'name': 'load_max',
            'type': 'float',
            'description': '最大负荷(kW)',
            'required': 'True',
        },
        {
            'name': 'load_electricity',
            'type': 'float',
            'description': '年用电量(kWh)',
            'required': 'True',
        },
        {
            'name': 'storage_w_cost',
            'type': 'float',
            'description': '储能系统的功率单位造价(元/W)',
            'required': 'True',
        },
        {
            'name': 'storage_wh_cost',
            'type': 'float',
            'description': '储能系统的容量单位造价(元/Wh)',
            'required': 'True',
        },
        {
            'name': 'pv_cost',
            'type': 'float',
            'description': '光伏系统的功率单位造价(元/W)',
            'required': 'True',
        },
        {
            'name': 'pv_nom0',
            'type': 'float',
            'description': '已建光伏系统规模(kW)',
            'required': 'True',
        },
        {
            'name': 'pv_optimize',
            'type': 'bool',
            'description': '是否对光伏系统新建规模进行优化(true|false)',
            'required': 'True',
        },
        {
            'name': 'wind_cost',
            'type': 'float',
            'description': '风电系统的功率单位造价(元/W)',
            'required': 'True',
        },
        {
            'name': 'wind_nom0',
            'type': 'float',
            'description': '已建风电系统规模(kW)',
            'required': 'True',
        },
        {
            'name': 'wind_optimize',
            'type': 'bool',
            'description': '是否对风电系统新建规模进行优化(true|false)',
            'required': 'True',
        },
        {
            'name': 'up_flow_max_proportion',
            'type': 'float',
            'description': '新能源倒送到电网的电量的最大比例(0.0-1.0)',
            'required': 'True',
        },
        {
            'name': 'down_flow_max_proportion',
            'type': 'float',
            'description': '电网下送电量的最大比例(0.0-1.0)',
            'required': 'True',
        },
    ]
    def __init__(self):
        pass

    def call(self, in_thoughts):
        dict_string = legacy_extract_dict_string(in_thoughts)
        dict = json5.loads(dict_string)
        print(Global.line)
        print(f'Energy_Investment_Plan_Tool的输入参数dict为: {dict}')
        print(Global.line)

        action_result = ''
        try:
            import requests
            from requests.exceptions import RequestException
            # req = {
            #     'rate': 0.08,
            #
            #     'pv_nom0': 0,
            #     'pv_cost': 3.5,
            #     'pv_optimize': True,
            #
            #     'wind_nom0': 0,
            #     'wind_cost': 3.5,
            #     'wind_optimize': True,
            #
            #     'storage_w_cost': 0.12,
            #     'storage_wh_cost': 1.38 * 0.6,
            #
            #     'up_flow_max_proportion': 0.2,
            #     'down_flow_max_proportion': 0.1,
            #
            #     'load_max': 800 * 1000,
            #     'load_electricity': 800 * 1000 * 6400,
            #
            #     'simu_years': 10,
            # }
            req = dict['tool_parameters']
            response = requests.post(url='http://116.62.63.204:18001/cal/', json=req)
            response.raise_for_status()  # 如果不在200-400，发出一个异常
            rtn_table = response.json()
            # print(f'NPS服务器返回的结果为: \n{rtn_table}')
        except RequestException as e:
            action_result = f'Energy_Investment_Plan_Tool请求API时，服务器报错：{e}'

        # action_result = f'Energy_Investment_Plan_Tool返回的结果汇总为: \n{rtn_table}'
        action_result = f'Energy_Investment_Plan_Tool返回的结果汇总为: \n{rtn_table}\n 请返回整理结果和报告url'
        # action_result = '[最终答复]Energy_Investment_Plan_Tool()尚未完整实现.'
        return action_result
