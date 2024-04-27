import streamlit as st
import subprocess
import re
import os
import time
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx

import pandas as pd
import numpy as np

# 设置IPMI密码的环境变量
password = 'jackseaver'

st.set_page_config(
    initial_sidebar_state="collapsed",
    page_title="Life-Agent",
    layout="wide",
)


@st.cache_resource  # cache_resource主要用于访问db connection等仅调用一次的全局资源
def llm_init():
    pass


def on_chat_input_submit():
    pass

# 'CPU1 Temp': 43.000
# 'CPU2 Temp': 44.000
# 'Inlet Temp': 29.000
# 'PCH Temp': 47.000
# 'System Temp': 37.000
# 'Peripheral Temp': 51.000
# 'MB_10G Temp': 61.000
# 'P1-DIMMA1 Temp': 37.000
# 'P1-DIMMA2 Temp': na
# 'P1-DIMMB1 Temp': 36.000
# 'P1-DIMMB2 Temp': na
# 'P1-DIMMC1 Temp': 36.000
# 'P1-DIMMC2 Temp': na
# 'P1-DIMMD1 Temp': 35.000
# 'P1-DIMMD2 Temp': na
# 'P1-DIMME1 Temp': na
# 'P1-DIMME2 Temp': na
# 'P1-DIMMF1 Temp': na
# 'P1-DIMMF2 Temp': na
# 'P2-DIMMA1 Temp': 38.000
# 'P2-DIMMA2 Temp': na
# 'P2-DIMMB1 Temp': 35.000
# 'P2-DIMMB2 Temp': na
# 'P2-DIMMC1 Temp': 34.000
# 'P2-DIMMC2 Temp': na
# 'P2-DIMMD1 Temp': 34.000
# 'P2-DIMMD2 Temp': na
# 'P2-DIMME1 Temp': na
# 'P2-DIMME2 Temp': na
# 'P2-DIMMF1 Temp': na
# 'P2-DIMMF2 Temp': na
# 'FAN1': 3200.000
# 'FAN2': 3200.000
# 'FAN3': 3200.000
# 'FAN4': 3200.000
# 'FAN5': 3200.000
# 'FAN6': 3200.000
# 'FAN7': 3200.000
# 'FAN8': 3200.000
# 'FAN9': 3900.000
# 'FAN10': 3700.000
# 'NVMe_SSD Temp': 41.000
# gpu[0]: {'Fan': '34%', 'Temp': '42C', 'Pwr:Usage': '43W', 'Pwr:Cap': '200W', 'Mem-Used': '20612MiB', 'Mem-Total': '22528MiB', 'GPU-Util': '0%'}
# gpu[1]: {'Fan': '34%', 'Temp': '42C', 'Pwr:Usage': '35W', 'Pwr:Cap': '200W', 'Mem-Used': '20588MiB', 'Mem-Total': '22528MiB', 'GPU-Util': '0%'}
# gpu[2]: {'Fan': '35%', 'Temp': '38C', 'Pwr:Usage': '33W', 'Pwr:Cap': '200W', 'Mem-Used': '20584MiB', 'Mem-Total': '22528MiB', 'GPU-Util': '0%'}
# gpu[3]: {'Fan': '34%', 'Temp': '41C', 'Pwr:Usage': '29W', 'Pwr:Cap': '200W', 'Mem-Used': '20584MiB', 'Mem-Total': '22528MiB', 'GPU-Util': '0%'}
# gpu[4]: {'Fan': '27%', 'Temp': '40C', 'Pwr:Usage': '38W', 'Pwr:Cap': '200W', 'Mem-Used': '20584MiB', 'Mem-Total': '22528MiB', 'GPU-Util': '0%'}
# gpu[5]: {'Fan': '35%', 'Temp': '43C', 'Pwr:Usage': '32W', 'Pwr:Cap': '200W', 'Mem-Used': '20584MiB', 'Mem-Total': '22528MiB', 'GPU-Util': '0%'}
# gpu[6]: {'Fan': '36%', 'Temp': '48C', 'Pwr:Usage': '32W', 'Pwr:Cap': '200W', 'Mem-Used': '20584MiB', 'Mem-Total': '22528MiB', 'GPU-Util': '0%'}
# gpu[7]: {'Fan': '38%', 'Temp': '51C', 'Pwr:Usage': '43W', 'Pwr:Cap': '200W', 'Mem-Used': '20584MiB', 'Mem-Total': '22528MiB', 'GPU-Util': '0%'}

def get_temp_and_fan_info():
    temp_info_dict = {}

    report = _get_ipmitool_sensor_report()

    temp_info_dict['CPU1 Temp'] = _get_temp_from_report(report, 'CPU1 Temp')
    temp_info_dict['CPU2 Temp'] = _get_temp_from_report(report, 'CPU2 Temp')
    temp_info_dict['Inlet Temp'] = _get_temp_from_report(report, 'Inlet Temp')
    temp_info_dict['PCH Temp'] = _get_temp_from_report(report, 'PCH Temp')
    temp_info_dict['System Temp'] = _get_temp_from_report(report, 'System Temp')
    temp_info_dict['Peripheral Temp'] = _get_temp_from_report(report, 'Peripheral Temp')
    temp_info_dict['MB_10G Temp'] = _get_temp_from_report(report, 'MB_10G Temp')

    temp_info_dict['P1-DIMMA1 Temp'] = _get_temp_from_report(report, 'P1-DIMMA1 Temp')
    temp_info_dict['P1-DIMMA2 Temp'] = _get_temp_from_report(report, 'P1-DIMMA2 Temp')

    temp_info_dict['P1-DIMMB1 Temp'] = _get_temp_from_report(report, 'P1-DIMMB1 Temp')
    temp_info_dict['P1-DIMMB2 Temp'] = _get_temp_from_report(report, 'P1-DIMMB2 Temp')

    temp_info_dict['P1-DIMMC1 Temp'] = _get_temp_from_report(report, 'P1-DIMMC1 Temp')
    temp_info_dict['P1-DIMMC2 Temp'] = _get_temp_from_report(report, 'P1-DIMMC2 Temp')

    temp_info_dict['P1-DIMMD1 Temp'] = _get_temp_from_report(report, 'P1-DIMMD1 Temp')
    temp_info_dict['P1-DIMMD2 Temp'] = _get_temp_from_report(report, 'P1-DIMMD2 Temp')

    temp_info_dict['P1-DIMME1 Temp'] = _get_temp_from_report(report, 'P1-DIMME1 Temp')
    temp_info_dict['P1-DIMME2 Temp'] = _get_temp_from_report(report, 'P1-DIMME2 Temp')

    temp_info_dict['P1-DIMMF1 Temp'] = _get_temp_from_report(report, 'P1-DIMMF1 Temp')
    temp_info_dict['P1-DIMMF2 Temp'] = _get_temp_from_report(report, 'P1-DIMMF2 Temp')


    temp_info_dict['P2-DIMMA1 Temp'] = _get_temp_from_report(report, 'P2-DIMMA1 Temp')
    temp_info_dict['P2-DIMMA2 Temp'] = _get_temp_from_report(report, 'P2-DIMMA2 Temp')

    temp_info_dict['P2-DIMMB1 Temp'] = _get_temp_from_report(report, 'P2-DIMMB1 Temp')
    temp_info_dict['P2-DIMMB2 Temp'] = _get_temp_from_report(report, 'P2-DIMMB2 Temp')

    temp_info_dict['P2-DIMMC1 Temp'] = _get_temp_from_report(report, 'P2-DIMMC1 Temp')
    temp_info_dict['P2-DIMMC2 Temp'] = _get_temp_from_report(report, 'P2-DIMMC2 Temp')

    temp_info_dict['P2-DIMMD1 Temp'] = _get_temp_from_report(report, 'P2-DIMMD1 Temp')
    temp_info_dict['P2-DIMMD2 Temp'] = _get_temp_from_report(report, 'P2-DIMMD2 Temp')

    temp_info_dict['P2-DIMME1 Temp'] = _get_temp_from_report(report, 'P2-DIMME1 Temp')
    temp_info_dict['P2-DIMME2 Temp'] = _get_temp_from_report(report, 'P2-DIMME2 Temp')

    temp_info_dict['P2-DIMMF1 Temp'] = _get_temp_from_report(report, 'P2-DIMMF1 Temp')
    temp_info_dict['P2-DIMMF2 Temp'] = _get_temp_from_report(report, 'P2-DIMMF2 Temp')


    temp_info_dict['FAN1'] = _get_temp_from_report(report, 'FAN1')
    temp_info_dict['FAN2'] = _get_temp_from_report(report, 'FAN2')
    temp_info_dict['FAN3'] = _get_temp_from_report(report, 'FAN3')
    temp_info_dict['FAN4'] = _get_temp_from_report(report, 'FAN4')
    temp_info_dict['FAN5'] = _get_temp_from_report(report, 'FAN5')
    temp_info_dict['FAN6'] = _get_temp_from_report(report, 'FAN6')
    temp_info_dict['FAN7'] = _get_temp_from_report(report, 'FAN7')
    temp_info_dict['FAN8'] = _get_temp_from_report(report, 'FAN8')
    temp_info_dict['FAN9'] = _get_temp_from_report(report, 'FAN9')
    temp_info_dict['FAN10'] = _get_temp_from_report(report, 'FAN10')

    temp_info_dict['NVMe_SSD Temp'] = _get_temp_from_report(report, 'NVMe_SSD Temp')

    return temp_info_dict

def _get_temp_from_report(report, temp_name):
    for line in report:
        if temp_name in line:
            temp = line.split('|')[1].strip()
            return temp
    return f'{temp_name} not found'

def _get_ipmitool_sensor_report():
    command = 'sudo ipmitool sensor'
    full_command = 'echo {} | {}'.format(password, command)
    output = subprocess.run(full_command, shell=True, check=True, capture_output=True)
    # output = subprocess.check_output(['sudo', '-S', 'ipmitool', 'sensor'], stdin=subprocess.PIPE)
    # output = subprocess.check_output(['sudo', 'ipmitool', 'sensor'])
    lines = output.stdout.decode().split('\n')
    return lines

def get_gpu_info_list(report, gpu_name='NVIDIA GeForce RTX 2080 Ti'):
    gpu_temp_info_list = []
    for i in range(len(report)):
        if gpu_name in report[i]:
            line = report[i+1]
            line = line.replace('|', ' ')
            line = line.replace('/', ' ')
            matches = re.sub(r'\s+', ' ', line)
            data_list = matches.strip().split(' ')
            # for data in data_list:
            #     print(f'{data}+', end='', flush=True)
            gpu_temp_info = {
                'Fan':          data_list[0],
                'Temp':         data_list[1],
                'Pwr:Usage':    data_list[3],
                'Pwr:Cap':      data_list[4],
                'Mem-Used':     data_list[5],
                'Mem-Total':    data_list[6],
                'GPU-Util':     data_list[7],
            }
            gpu_temp_info_list.append(gpu_temp_info)
    return gpu_temp_info_list

def _get_nvidia_smi_report():
    output = subprocess.check_output(['nvidia-smi'])
    lines = output.decode().split('\n')
    return lines

def get_temp_info_and_gpu_info():
    temperature_and_fan_dict = get_temp_and_fan_info()
    # for key, value in temperature_and_fan_dict.items():
    #     print(f"'{key}': {value}")

    gpu_report = _get_nvidia_smi_report()
    gpu_info_list = get_gpu_info_list(gpu_report)

    # for i in range(len(gpu_info_list)):
    #     print(f'gpu[{i}]: {gpu_info_list[i]}')

    return temperature_and_fan_dict, gpu_info_list

def get_status():
    state = st.session_state

    state.temperature_and_fan_dict, state.gpu_info_list = get_temp_info_and_gpu_info()

    state.temp_list = []  # [ ['cpu1', 25.0], ... ]
    state.temp_color_list = []

    state.fan_list = []  # [ ['fan1', 3200], ... ]
    state.fan_color_list = []

    state.gpu_list = []

    for k, v in state.temperature_and_fan_dict.items():
        if not 'FAN' in k:
            if 'na' in v:
                # 温度为na，设置为0、颜色为'C'
                state.temp_list.append([k, 'n/a'])
                state.temp_color_list.append('#ff0000')
            elif float(v) < 40:
                # 温度为0-40
                state.temp_list.append([k, v])
                state.temp_color_list.append('#00ff00')
            elif float(v) < 60:
                # 温度为40-60
                state.temp_list.append([k, v])
                state.temp_color_list.append('#228800')
            elif float(v) < 80:
                # 温度为60-80
                state.temp_list.append([k, v])
                state.temp_color_list.append('#444400')
            elif float(v) < 90:
                # 温度为80-90
                state.temp_list.append([k, v])
                state.temp_color_list.append('#882200')
            else:
                # 温度为>90
                state.temp_list.append([k, v])
                state.temp_color_list.append('#ff0000')

    for k, v in state.temperature_and_fan_dict.items():
        if 'FAN' in k:
            state.fan_list.append([k, v])

    state.temp_data = pd.DataFrame(state.temp_list, columns=['元件', '温度(℃)'])
    state.temp_data['color'] = state.temp_color_list
    state.fan_data = pd.DataFrame(state.fan_list, columns=['风扇', '转速(RPM)'])
    sidebar = st.sidebar
def streamlit_refresh_loop():
    st.title("System Info")
    state = st.session_state

    get_status()
    # state.temperature_and_fan_dict, state.gpu_info_list = get_temp_info_and_gpu_info()
    #
    # state.temp_list = []  # [ ['cpu1', 25.0], ... ]
    # state.temp_color_list = []
    #
    # state.fan_list = []  # [ ['fan1', 3200], ... ]
    # state.fan_color_list = []
    #
    # state.gpu_list = []
    #
    # for k, v in state.temperature_and_fan_dict.items():
    #     if not 'FAN' in k:
    #         if 'na' in v:
    #             # 温度为na，设置为0、颜色为'C'
    #             state.temp_list.append([k, 'n/a'])
    #             state.temp_color_list.append('#ff0000')
    #         elif float(v) < 40:
    #             # 温度为0-40
    #             state.temp_list.append([k, v])
    #             state.temp_color_list.append('#00ff00')
    #         elif float(v) < 60:
    #             # 温度为40-60
    #             state.temp_list.append([k, v])
    #             state.temp_color_list.append('#228800')
    #         elif float(v) < 80:
    #             # 温度为60-80
    #             state.temp_list.append([k, v])
    #             state.temp_color_list.append('#444400')
    #         elif float(v) < 90:
    #             # 温度为80-90
    #             state.temp_list.append([k, v])
    #             state.temp_color_list.append('#882200')
    #         else:
    #             # 温度为>90
    #             state.temp_list.append([k, v])
    #             state.temp_color_list.append('#ff0000')
    #
    # for k, v in state.temperature_and_fan_dict.items():
    #     if 'FAN' in k:
    #         state.fan_list.append([k, v])

    # state.temp_data = pd.DataFrame(state.temp_list, columns=['元件', '温度(℃)'])
    # state.temp_data['color'] = state.temp_color_list
    # state.fan_data = pd.DataFrame(state.fan_list, columns=['风扇', '转速(RPM)'])

    sidebar = st.sidebar

    # =============================expander：对话参数==============================
    exp1 =  sidebar.expander("控制参数", expanded=True)
    state.cpu1_temp = exp1.markdown(f"CPU1 温度: &emsp;{state.temperature_and_fan_dict['CPU1 Temp']}℃")
    state.cpu2_temp = exp1.markdown(f"CPU2 温度: &emsp;{state.temperature_and_fan_dict['CPU2 Temp']}℃")
    state.nvme_temp = exp1.markdown(f"NVME 温度: &emsp;{state.temperature_and_fan_dict['NVMe_SSD Temp']}℃")
    state.mb10_temp = exp1.markdown(f"MB10 温度: &emsp;{state.temperature_and_fan_dict['MB_10G Temp']}℃")
    state.inle_temp = exp1.markdown(f"INLE 温度: &emsp;{state.temperature_and_fan_dict['Inlet Temp']}℃")
    state.syst_temp = exp1.markdown(f"SYST 温度: &emsp;{state.temperature_and_fan_dict['System Temp']}℃")
    state.peri_temp = exp1.markdown(f"PERI 温度: &emsp;{state.temperature_and_fan_dict['Peripheral Temp']}℃")
    state.temp1 = exp1.number_input(label="温度阈值1(℃):",  placeholder=45.0, max_value=45.0, min_value=0.0, step=1.0, value=45.0)
    state.temp2 = exp1.number_input(label="温度阈值2(℃):",  placeholder=50.0, max_value=50.0, min_value=0.0, step=1.0, value=50.0)
    state.temp3 = exp1.number_input(label="温度阈值3(℃):",  placeholder=60.0, max_value=60.0, min_value=0.0, step=1.0, value=60.0)
    state.temp4 = exp1.number_input(label="温度阈值4(℃):",  placeholder=65.0, max_value=65.0, min_value=0.0, step=1.0, value=65.0)

    draw_chart()

    # while True:
    #     state.temp_data = pd.DataFrame(state.temp_list, columns=['元件', '温度(℃)'])
    #     state.temp_data['color'] = state.temp_color_list
    #     state.fan_data = pd.DataFrame(state.fan_list, columns=['风扇', '转速(RPM)'])
    #     # chart()
    #     # st.rerun()
    #     time.sleep(10)

    g_data_refresher.start()

class Data_Refresher():
    def __init__(self):
        self.task = None
        self.started = False

    def run(self):
        state = st.session_state

        while True:
            get_status()

            # chart()
            # st.rerun()
            for i in range(len(state.temp_list)):
                if 'CPU' in state.temp_list[i][0]:
                    print(f'{state.temp_list[i][0]} \t {state.temp_list[i][1]} \t {state.temp_color_list[i]}')
            print()

            time.sleep(10)

    def start(self):
        if not self.started:
            self.started = True

            self.task = threading.Thread(target=self.run)
            add_script_run_ctx(self.task)
            self.task.start()

@st.cache_resource
def init_data_refresher():
    data_refresher = Data_Refresher()
    return data_refresher

g_data_refresher = init_data_refresher()


@st.experimental_fragment
def draw_chart():
    state = st.session_state

    state.draw_chart = st.scatter_chart(state.temp_data, x='元件', y='温度(℃)', color='color')
    st.scatter_chart(state.fan_data, x='风扇', y='转速(RPM)')

if __name__ == "__main__":
    streamlit_refresh_loop()

