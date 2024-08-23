from pprint import pprint

from singleton import singleton
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
import config

from utils.task import Status
from redis_client import Redis_Client
from config import dred,dgreen, dblue
from tools.llm.api_client import LLM_Client
import time, json5

from redis_proxy.custom_command.protocol import server_add_task, server_invoking_command
from redis_proxy.custom_bridge.protocol import server_add_and_start_bridge_servant
from redis_proxy.thread import Task_Worker_Thread, Redis_Proxy_Server_Thread
from protocol import Key_Name_Space

from redis_proxy.custom_command.protocol import call_custom_command

from redis_proxy.custom_command.llm.protocol import Redis_Proxy_Command_LLM

from redis_proxy.custom_command.llm.servant import llm_servant

def Redis_Proxy_Server_Callback(out_task_info_must_be_here):
    thread_status = out_task_info_must_be_here

    def cancel():
        dred(f"Redis Proxy Server ({thread_status['task_name']}) cancelling...")

    def __pop_stream(key):
        return s_redis_client.pop_stream(key)


    # 注册各种类型的任务
    def __add_task(inout_client_data, task_id, task_type):
        server_add_task(inout_client_data, task_id, task_type)

    # 响应client的new task
    def polling_new_tasks():
        # print(f's_redis_proxy_server_data: {s_redis_proxy_server_data}')
        dict_list = __pop_stream(key='Task_Register')
        for dict in dict_list:
            # print(f'new task dict: {dict}')
            # {'client_id': 'Client_7b8024f3-f88c-4756-97c3-c583252ce6e5', 'task_type': 'Redis_Task_Type.LLM', 'task_id': 'Task_41158011-e11e-4a3e-84f4-38fd87fba71d'}

            if 'client_id' in dict and 'task_type' in dict and 'task_id' in dict:
                cid = dict['client_id']
                tid = dict['task_id']
                ttype = dict['task_type']
                if cid in s_redis_proxy_server_data:
                    # 已有该client数据
                    pass
                else:
                    # 没有该client数据
                    s_redis_proxy_server_data[cid] = {
                    }

                __add_task(inout_client_data=s_redis_proxy_server_data[cid], task_id=tid, task_type=ttype)

    def polling_new_bridge():
        dict_list = __pop_stream(key='Bridge_Register')
        for dict in dict_list:
            if 'client_id' in dict and 'bridge_para_json5_string' in dict:
                # dgreen(f'polling_new_bridge() dict: {dict}')
                cid = dict['client_id']
                bridge_para = json5.loads(dict['bridge_para_json5_string'])
                if cid in s_redis_proxy_server_data:
                    # 已有该client数据
                    pass
                else:
                    # 没有该client数据
                    s_redis_proxy_server_data[cid] = {}

                server_add_and_start_bridge_servant(inout_client_data=s_redis_proxy_server_data[cid], s_redis_client=s_redis_client, bridge_para=bridge_para)

    # 执行command
    def __exec_command(**arg_dict):
        server_invoking_command(s_redis_proxy_server_data, s_redis_client, **arg_dict)

    # 响应client某task的command
    def polling_task_commands():
        has_bridge = False
        for k,v in s_redis_proxy_server_data.items():
            # 所有client_id
            for k1,v1 in v.items():
                if k1=='bridge_system':
                    has_bridge = True
                    # 注意，由于s_redis_proxy_server_data中，'bridge_system'和'Task_idxxxx'平行，因此必须排除掉
                    continue

                # 所有task_id
                task_id = k1

                task_data = v1

                # 查询该task下的command
                # 识别task中是否有桥接的关键判断，改为在client下注册bridge而非task下。防止第一个task的command过来时，随机情况下bridge未得到处理的的问题，即必须在command之前完成桥接。
                if has_bridge and 'task_command_key_bridged' in task_data:
                    # assert 'task_command_key_bridged' in task_data
                # if 'task_command_key_bridged' in task_data:
                #     dred(f'--------------------------------------------------------')
                #     dred(f"'task_command_key_bridged' in task_data, stream-key is bridged from '{f'Task_{task_id}_Command'}' to '{task_data['task_command_key_bridged']}'.")
                #     dred(f'--------------------------------------------------------')
                    stream_key = task_data['task_command_key_bridged']
                    # dblue(f'stream_key1: {stream_key}')
                else:
                    stream_key = f'Task_{task_id}_Commands'
                    # dblue(f'stream_key0: {stream_key}')

                dict_list = __pop_stream(key=stream_key)

                # 执行所有command
                for command_para_dict in dict_list:
                    dred(f'exec_command: ')
                    pprint(command_para_dict)
                    __exec_command(**command_para_dict)

    # Redis Proxy Server 主循环
    count = 0
    while True:
        count += 1
        if thread_status['status']==Status.Cancelling:
            # cancel中
            cancel()
            dred(f"Redis Task Server ({thread_status['task_name']}) cancelled")
            break

        # polling_new_tasks()
        # polling_new_bridge()
        # polling_task_commands()

        # show living per 10*redis_proxy_server_sleep_time
        # if count % 10 == 0:
        # dgreen(f"Redis Proxy Server ({thread_status['status']}) living...")

        # time.sleep(2)
        time.sleep(config.Global.redis_proxy_server_sleep_time)

def server_init():
    global s_redis_proxy_server_data, s_redis_client, s_redis_proxy_server_thread

    s_redis_proxy_server_data = {}

    IS_SERVER = True
    if IS_SERVER:
        # 启动 Redis Task Server
        s_redis_client = Redis_Client(
            host=config.Domain.redis_server_domain,
            port=config.Port.redis_client,
            invoker='redis_proxy_server(legacy)'
        )

        # redis清空所有数据
        s_redis_client.flushdb()

        # s_redis_client = Redis_Client(host='localhost', port=6379)  # win-server
        s_redis_proxy_server_thread = Redis_Proxy_Server_Thread()
        s_redis_proxy_server_thread.init(Redis_Proxy_Server_Callback)
        # s_redis_task_server.init(Redis_Task_Server_Callback, in_timeout=5)
        s_redis_proxy_server_thread.start()

# @dataclass
# class Bridge_Data:
#     obj: Optional[Any] = None
#     thread: Optional[Any] = None
#
# @dataclass
# class Bridge_System:
#     bridge_types: Dict[str, Bridge_Data] = field(default_factory=dict)

@dataclass
class Command_Data:
    cmd_id: str = ''
    cmd_thread: Any = None
    cmd_status_key: Optional[str] = None
    cmd_result_key: Optional[str] = None

@dataclass
class Task_Data:
    task_id: str = ''
    task_type: str = ''
    task_status_key: str = ''
    task_result_key: str = ''
    task_obj: Any = None
    commands: Dict[str, Command_Data] = field(default_factory=dict)
    # task_command_key_bridged: Optional[str] = None
    # task_status: str = ''

    def add_command_data(self, command_id, command_data, task_obj):
        self.task_obj = task_obj
        cmd_id = command_id
        cmd_data = asdict(Command_Data(
            cmd_id=cmd_id,
        ))
        self.commands[cmd_id] = cmd_data

@dataclass
class Client_Data:
    client_id: str = ''
    tasks: Dict[str, Task_Data] = field(default_factory=dict)
    # bridge_system: Optional[Bridge_System] = None

    def add_task_data(self, task_data):
        task_id = task_data.task_id
        self.tasks[task_id] = task_data

@dataclass
class Server_Data:
    server_id: str = ''
    clients: Dict[str, Client_Data] = field(default_factory=dict)

    def check_if_new_client_data(self, client_id):
        if client_id in self.clients:
            pass
        else:
            client_data = Client_Data(client_id=client_id)
            self.clients[client_id] = client_data

# Redis_Proxy_Server（单体）
# 功能：实现server侧资源的异步调用（如LLM、LLM-Agent、SD等）
# server侧所维护对象的关系：
#   [1]redis_proxy_server   <-> [i]client   # 多个client需要自己不同的状态
#   [1]client               <-> [j]task     # 1个client可以有多个不同或相同类型的task(如不同的LLM对话、SD应用)
#   [1]task                 <-> [k]command  # 1个client的1个task中可以有多个command(如1个LLM的历史相关的多次ask)
@singleton
class Redis_Proxy_Server:
    def __init__(self):
        self.server_thread = None           # server的polling线程
        self.server_data = Server_Data()    # server的clients状态数据
        self.redis_client = None            # server的redis调用接口

        self.inited = False                 # server是否完成初始化

    def _start_server_thread(self):
        self.server_thread = Redis_Proxy_Server_Thread()
        self.server_thread.init(self._callback)
        self.server_thread.start()
        dgreen(f'{self.server_data.server_id}的polling线程已启动.')

    def _get_new_task_paras(self, task_data_dict):
        pass

    # 查询client是否有新的task，将task信息存入server_data
    def _polling_new_task(self):
        # 获取client注册task的stream_key名称
        tasks_stream_key = Key_Name_Space.Task_Register
        # 读取redis中的task的stream
        gen = self.redis_client.pop_stream_gen(tasks_stream_key)
        for task_data_dict in gen:
            dgreen(f'-----------------获得new task----------------')
            pprint(task_data_dict)
            dgreen(f'--------------------------------------------')

            # 在server_data中创建新的task信息
            dgreen(f'-----------------new task信息创建前----------------')
            pprint(self.server_data)

            # 读取来自client侧的注册信息
            client_id = task_data_dict['client_id']
            task_id = task_data_dict['task_id']
            task_type = task_data_dict['task_type']

            # 若server_data没用client_data，需要新建client_data
            self.server_data.check_if_new_client_data(client_id)

            # 新建task_data
            task_data = Task_Data(
                task_id=task_id,
                task_type=task_type,
            )
            self.server_data.clients[client_id].add_task_data(task_data)
            dgreen(f'-----------------new task信息已创建----------------')
            pprint(self.server_data)
            dgreen(f'-------------------------------------------------')

    # yield每一个task_id
    def _search_all_tasks_gen(self):
        for k1,v1 in self.server_data.clients.items():
            # 获取client_data
            client_data = v1
            for k2,v2 in client_data.tasks.items():
                # 获取task_data
                task_data = v2
                # 返回task_id
                yield task_data.task_id


    def _polling_new_command(self):
        # 获取client注册command的stream_key名称
        commands_key_format = Key_Name_Space.Commands_Register

        # 遍历所有task_id
        for task_id in self._search_all_tasks_gen():
            # dred(f'-----------------task_id:{task_id}----------------')
            # 获取task_stream_key，如：'Task_{task_id}_Commands'.format(task_id=task_id)
            commands_stream_key = commands_key_format.format(task_id=task_id)

            # 遍历所有command
            gen = self.redis_client.pop_stream_gen(stream_key=commands_stream_key)
            for command_data_dict in gen:
                dgreen(f'-----------------获得new command----------------')
                pprint(command_data_dict)
                client_id = command_data_dict['client_id']
                task_id = command_data_dict['task_id']
                command = command_data_dict['command']
                command_id = command_data_dict['command_id']

                del command_data_dict['client_id']
                del command_data_dict['task_id']
                del command_data_dict['command_id']
                del command_data_dict['command']

                # 获取tasks_data_dict
                task_data_dict = self.server_data.clients[client_id].tasks[task_id]

                # 调用自定义command的servant
                task_type = task_data_dict.task_type
                task_obj = task_data_dict.task_obj

                # client输出chunk(可以是text stream的chunk，也可以是一张图片string)的回调函数
                def _output_callback(output_string:str, use_byte:bool):
                    result_stream_key = Key_Name_Space.Results_Register.format(task_id=task_id, command_id=command_id)
                    chunk_data = {
                        'chunk_data_type': 'text',
                        'chunk': output_string,
                        'chunk_use_byte': int(use_byte),
                        'status': 'running',
                    }
                    self.redis_client.add_stream(stream_key=result_stream_key, data=chunk_data)

                # client输出结束的回调函数
                def _finished_callback():
                    result_stream_key = Key_Name_Space.Results_Register.format(task_id=task_id, command_id=command_id)
                    chunk_data = {
                        'status': 'completed',
                    }
                    self.redis_client.add_stream(stream_key=result_stream_key, data=chunk_data)

                return_task_obj = call_custom_command(
                    task_type=task_type,
                    command=command,
                    command_id=command_id,
                    task_obj=task_obj,
                    output_callback=_output_callback,
                    finished_callback=_finished_callback,
                    **command_data_dict
                )

                # 创建server侧的command信息
                task_data_dict.add_command_data(
                    command_id=command_id,
                    command_data=command_data_dict,
                    task_obj=return_task_obj
                )

                server_invoking_command(
                    self.server_data,
                    self.redis_client,
                    task_id=task_id,
                    client_id=client_id,
                    command=command,
                    command_id=command_id,
                    **command_data_dict
                )
                dgreen(f'-----------------------------------------------')

    def _callback(self, out_task_info_must_be_here):
        # polling线程的回调内容
        while True:
            self._polling_new_task()
            self._polling_new_command()
            time.sleep(config.Global.redis_proxy_server_sleep_time)

    def init(self):
        if self.inited:
            return
        # 初始化server信息
        self.server_data.server_hostname = config.get_hostname()
        self.server_data.server_local_ip = config.get_local_ip()
        self.server_data.server_id = f'Redis_Proxy_Server(singleton: {self.server_data.server_hostname}, { self.server_data.server_local_ip})'
        dgreen(f'{self.server_data.server_id}初始化中...')

        # 初始化redis_client
        self.redis_client = Redis_Client(
            host=config.Domain.redis_server_domain,
            port=config.Port.redis_client,
            invoker='Redis_Proxy_Server(singleton)'
        )
        dgreen(f'{self.server_data.server_id}的Redis_Client({config.Domain.redis_server_domain}:{config.Port.redis_client})初始化完毕.')

        # 清空本应用再redis server上的数据
        self.redis_client.flushdb()
        dgreen(f'{self.server_data.server_id}清空redis数据库完毕.')

        # 启动polling线程
        self._start_server_thread()


        self.inited = True
        dgreen(f'{self.server_data.server_id}初始化完毕.')

# Redis_Proxy_Server（单体）的legacy数据示意
# s_redis_proxy_server_data = {
    # 'client-id1' : {
    #     'bridge_system' : [
    #         'bridge_type1': {
    #             'obj': None,
    #             'thread': None,
    #         },
    #     ],
    #     'task-id1' : {
    #         'task_command_key_bridged':'Task_{task_id}_Command_Bridged',  # 这一行由servant注入，如果有了，表明现需要对command stream进行桥接
    #         'task_type' : str(Redis_Task_Type.LLM),
    #         'task_status_key' : '',
    #         'task_result_key' : '',   # 完整的cmd key是：data['task_result_key'] + "_cmd_xxxx"
    #         'command_system' : {
    #               'obj': llm_client,
    #               'thread': llm_client_thread,
    #               'cmd_id1': {
    #                   'cmd_status_key': None, # 'cmd_status_key': f'Task_{task_id}_Status_CMD_{cmd_id}
    #                   'cmd_result_key': None, # 'cmd_result_key': f'Task_{task_id}_Result_CMD_{cmd_id}
    #               },
    #               'cmd_id2': {
    #                   'cmd_status_key': None, # 'cmd_status_key': f'Task_{task_id}_Status_CMD_{cmd_id}
    #                   'cmd_result_key': None, # 'cmd_result_key': f'Task_{task_id}_Result_CMD_{cmd_id}
    #               },
    #         },
    #     },
    #     'task-id2' : {
    #         'task_type' : str(Redis_Task_Type.LLM),
    #         'task_status': '',
    #     },
    # },
    # 'client-id2' : {
    # },
# }

def main():
    server_init()
    while(1):
        time.sleep(1)

if __name__ == "__main__":
    print(config.get_local_ip())
    # print(config.get_public_ip())
    print(config.get_hostname())
    s1 = Redis_Proxy_Server()
    s2 = Redis_Proxy_Server()
    print(s1==s2)
    s1.init()
    s2.init()
    main()