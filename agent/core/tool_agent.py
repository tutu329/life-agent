# pip install pyinstaller
# -----------用pyinstaller生成可执行代码-----------
# 在/home/tutu/server/life-agent下：
# 正常运行代码是：
# python -m agent.tool_agent
# 转换代码是：
# pyinstaller agent/tool_agent.py --paths=. --distpath ~/
# 其中“--paths=.”表示将/home/tutu/server/life-agent加入到PyInstaller分析路径中，以便找到tools模块
# 可执行代码将输出至~/tool_agent/下，包括可执行代码和关联so等文件

from concurrent.futures import ThreadPoolExecutor
import time

import config
from config import dred, dgreen, dblue, dyellow
from agent.core.agent_base import Agent_Base
# from server_manager.web_server_base import Web_Server_Base
from agent.core.agent_config import Agent_Config
from utils.extract import extract_tool_dict
from uuid import uuid4

from typing import List

from tools.llm.api_client import LLM_Client
from agent.tools.base_tool import PROMPT_REACT
from agent.tools.base_tool import Base_Tool
from agent.tools.protocol import create_tool_ctx, get_tool_ctx, update_tool_context_info
# from agent.core.legacy_protocol import create_tool_ctx, get_tool_ctx, update_tool_context_info
from agent.tools.protocol import Action_Result
# from agent.core.legacy_protocol import Action_Result
from agent.tools.tool_manager import legacy_get_all_local_tools_class
from agent.core.protocol import Agent_Status, Agent_Stream_Queues, Query_Agent_Context
from agent.experience.agent_experience import Agent_Experience
from agent.tools.protocol import Tool_Call_Paras

import llm_protocol
from llm_protocol import LLM_Config, LLM_Query_Paras

from utils.fastapi_server import GeneratorDone

# 全局线程池，真正业务里可以按需设置 max_workers
g_thread_pool_executor = ThreadPoolExecutor()

class Tool_Agent(Agent_Base, Base_Tool):
# class Tool_Agent(Web_Server_Base, Base_Tool):
    # Base_Tool属性
        # name = 'Tool_Agent_As_Tool'
        # description = '本工具通过调用智能体解决问题。'
        # parameters = None

    # Base_Tool方法
    # def call(
    #         self,
    #         callback_tool_paras_dict,   # agent调用tool时的输入参数
    #         callback_agent_config,      # agent配置参数
    #         callback_agent_id,          # agent_id
    #         callback_last_tool_ctx,     # 上一个tool的上下文context(包含tool_task_id和可能的dataset_info)
    #         callback_father_agent_exp,  # agent_as_tool时，上级agent提供的经验exp
    # ):
    def call(self, tool_call_paras:Tool_Call_Paras):
        callback_tool_paras_dict = tool_call_paras.callback_tool_paras_dict
        callback_agent_config = tool_call_paras.callback_agent_config
        callback_top_agent_id = tool_call_paras.callback_top_agent_id
        callback_agent_id = tool_call_paras.callback_agent_id
        callback_last_tool_ctx = tool_call_paras.callback_last_tool_ctx
        callback_client_ctx = tool_call_paras.callback_client_ctx
        callback_father_agent_exp = tool_call_paras.callback_father_agent_exp

        # 本agent实例被用作tool调用
        tool_query = callback_tool_paras_dict['自然语言指令']
        dblue(f'agent_as_tool收到指令: "{tool_query}"')
        dblue(f'agent_as_tool收到para: \n"{callback_tool_paras_dict}"')

        # 将query和exp组合
        dyellow(f'---------------------agent_as_tool被調用(upper agent_id="{callback_agent_id}, top agent_id="{callback_top_agent_id}")------------------------------')
        if callback_father_agent_exp.strip():
            tool_query += tool_query + f'\n(获得了已有经验：{callback_father_agent_exp!r})'
        dyellow(f'upper agent的query: \n"{tool_query}"')
        dyellow(f'upper agent提供的经验: {callback_father_agent_exp!r}')
        dyellow(f'upper agent提供的tool_para: {callback_tool_paras_dict!r}')
        dyellow(f'upper agent提供的tool_context: {callback_last_tool_ctx!r}')
        dyellow(f'--------------------/agent_as_tool被調用(upper agent_id="{callback_agent_id}, top agent_id="{callback_top_agent_id}")------------------------------')

        self.run(query=tool_query, context=callback_client_ctx)
        # self.run(query=self.query_as_tool)
        action_result = Action_Result(result=self.get_final_answer())
        return action_result

    def _init_agent_data_in_server(self):
        # if self.agent_status_ref and self.agent_stream_queues_ref:
        #     self.agent_status_ref.started = True
            # self.agent_stream_queues_ref.output = print
        # else:
        self.status.started = True
            # self.stream_queues.output = print

    # def set_pause(self):
    #     self.agent_status_ref.paused = True
    #
    # def unset_pause(self):
    #     self.agent_status_ref.paused = False
    #
    # def is_paused(self):
    #     return self.agent_status_ref.paused

    def set_cancel(self):
        # if self.agent_status_ref:
        #     self.agent_status_ref.canceling = True
        # else:
        self.status.canceling = True
        dblue(f'【agent set_cancel() invoked】(agent_id="{self.agent_id}")')

    def unset_cancel(self):
        # if self.agent_status_ref:
        #     self.agent_status_ref.canceling = False
        #     self.agent_status_ref.canceled = False
        # else:
        self.status.canceling = False
        self.status.canceled = False
        dblue(f'【agent unset_cancel() invoked】(agent_id="{self.agent_id}")')

    def set_canceled(self):
        # if self.agent_status_ref:
        #     self.agent_status_ref.canceled = True
        # else:
        self.status.canceled = True
        dyellow(f'agent已经完成cancel.(agent_id: "{self.agent_id}")')

    def is_canceling(self):
        # if self.agent_status_ref:
        #     return self.agent_status_ref.canceling
        # else:
        return self.status.canceling

    # 注入top_agent_id(来自于upper agent)
    def set_top_agent_id(self, upper_agent):
        self.top_agent_id = upper_agent.top_agent_id

    # Tool_Agent方法
    def __init__(self,
                 tool_classes,
                 agent_config:Agent_Config,
                 query=None,                            # 用于as_tool(tool仅query一次)
                 as_tool_name=None,                     # As_Tool的name，如取: "Folder_Agent_As_Tool"
                 as_tool_description=None,              # As_Tool的description，如取: "本工具用来获取某个文件夹下的信息"
                 has_history = False,
                 tool_agent_experience_json_path='',    # 经验json文件，如果为‘’，就不设置经验
                 # agent_status_ref:Agent_Status=None,  # agent状态，由multi_agent_server管理
                 # agent_stream_queue_ref:Agent_Stream_Queues=None,  # agent的stream queue，，由multi_agent_server管理
                 top_agent_id=None,                     # top_agent_id为None时，表明自己即为top agent
                 ):
        Agent_Base.__init__(self)

        # 初始化Base_Tool实例
        # Base_Tool().__init__()

        # As_Tool属性
        self.tool_name = as_tool_name
        self.tool_description = as_tool_description

        # multi_agent_server管理的状态
        # self.agent_status_ref = agent_status_ref
        # self.agent_stream_queues_ref = agent_stream_queue_ref

        # 自身状态与multi_agent_server管理的状态同步，如果没有multi_agent_server状态，则自身初始化一套
        # if self.agent_status_ref:
        #     self.status = self.agent_status_ref
        # else:
        self.status = Agent_Status()

        # if self.agent_stream_queues_ref:
        #     self.stream_queues = self.agent_stream_queues_ref
        # else:
        self.stream_queues = Agent_Stream_Queues()

        # agent属性
        self.agent_id = str(uuid4())

        # 顶层的agent_id，主要用于多层agents系统中，让top_agent_id<-->connection，而与下层agent_id无关
        # top_agent_id的形成有2种情况：
        # 1）多层agents system中，靠parent agent注入
        # 2）自己即为top agent，则self.top_agent_id=self.agent_id
        if top_agent_id:
            # 外部注入了top_agent_id
            self.top_agent_id = top_agent_id
        else:
            # 外部没有注入top_agent_id
            self.top_agent_id = self.agent_id

        if not has_history:
            dyellow('--------------------------------------------------------------------------------------------')
            dyellow(f'Warning: agent没有设置history!(name:"{self.tool_name}", agent_id:"{self.agent_id}")')
            dyellow('--------------------------------------------------------------------------------------------')

        self.llm = None
        self.agent_config = agent_config
        self.has_history = has_history
        self.tool_agent_experience_json_path = tool_agent_experience_json_path

        self.last_tool_task_id = None   # 用于为下一个tool调用，提供上一个tool_task_id，从而获取上一个tool的context


        # self.temperature = self.agent_config.temperature
        # self.url = self.agent_config.base_url
        # self.api_key = self.agent_config.api_key
        # self.model_id = self.agent_config.llm_model_id
        self.agent_tools_description_and_full_history = ''
        # self.remove_content_in_think_pairs = remove_content_in_think_pairs  # 是否think模型

        self.current_query=None
        self.first_query=True

        self.query = query

        self.exp = None
        self.current_exp_str = ''

        self.tool_descs=''
        self.tool_names=[]
        self.tool_paras_just_outputed = False

        self.tool_classes = tool_classes
        # 创建一个字典，将工具名称映射到其实例
        self.registered_tool_instances_dict = {}
        for tool_cls in tool_classes:
            if isinstance(tool_cls, type):
                # 如果tool_cls是一个class
                tool_instance = tool_cls()
                tool_name = tool_cls.__name__
                self.registered_tool_instances_dict[tool_name] = tool_instance
            else:
                # 如果tool_cls是一个class的实例
                tool_instance = tool_cls
                tool_name = tool_instance.tool_name
                self.registered_tool_instances_dict[tool_name] = tool_instance

        dblue(f'【Agent(id={self.agent_id})的self.tool_classes】{self.tool_classes}')
        dblue(f'【Agent(id={self.agent_id})的self.registered_tool_instances_dict】{self.registered_tool_instances_dict}')

        # self.human = in_human    # 是否和human交互
        # self.action_stop = ['[观察]']
        # self.observation_stop = ['[观察]']
        self.response_stop = ['[观察]']
        # self.response_stop = ['<结束>']
        # self.response_stop = ['<res_stop>']
        self.turns_num = 0  # 用于统计当前对象的action轮次

        # self.ostream_end_func = self.agent_config.output_end               # 最终结果stream输出的end的func
        # self.ostream_use_chunk = self.agent_config.output_stream_use_chunk # 最终结果输出方式：chunk还是full_string
        # self.output_stream_to_console = self.agent_config.output_stream_to_console
        # self.sstream = self.agent_config.status_stream_buf                 # 中间状态输出的stream

        # self.status_list = inout_status_list     # 状态历史
        self.output_list = []     # 输出历史
        # self.output_list = self.agent_config.inout_output_list     # 输出历史

        self.__finished_keyword = '最终答复'
        self.final_answer = '尚未进行分析和答复'

        # 用于测试调用时长
        self._start_time = None
        self._end_time = None

    def init(self):
        self._init_agent_data_in_server()

        # self.llm = LLM_Client(
        #     url=self.url,
        #     api_key=self.api_key,
        #     model_id=self.model_id,
        #     temperature=self.temperature,
        #     history=False,
        #     print_input=False,
        #     max_new_tokens=config.LLM_Default.max_new_tokens
        # )

        self.agent_config.llm_config.has_history = False
        self.llm = LLM_Client(
            llm_config=self.agent_config.llm_config,
        )
        # self.agent_tools_description_and_full_history = PROMPT_REACT

        # 初始化experience
        if self.tool_agent_experience_json_path:
            self.exp = Agent_Experience(
                exp_json_file_path=self.tool_agent_experience_json_path,
                llm = self.llm,
                agent_id=self.agent_id,
            )
            # dyellow(f'----------------------agent经验系统成功初始化(agent_id="{self.agent_id}")------------------------')
            # dyellow(f"成功载入来自{self.tool_agent_experience_json_path!r}的经验")
            # dyellow(f'---------------------/agent经验系统成功初始化(agent_id="{self.agent_id}")------------------------')

        # 将所有工具转换为{tool_descs}和{tool_names}
        for tool in self.tool_classes:
            # 不论tool是Folder_Tool还是folder_agent_as_tool，都有name和description
            self.tool_names.append(f"'{tool.tool_name}'")
            self.tool_descs += '工具名称: ' + tool.tool_name + '\n'
            self.tool_descs += '工具描述: ' + tool.tool_description + '\n'
            self.tool_descs += '工具参数: [\n'

            dred(f'-----------------------tool.tool_parameters(tool.name="{tool.tool_name}")---------------------------')
            dblue(f'tool obj: "{tool}"')
            if hasattr(tool, 'tool_parameters'):
                dred(tool.tool_parameters)
            dred(f'----------------------/tool.tool_parameters(tool.name="{tool.tool_name}")---------------------------')
            if isinstance(tool, type):
                # 如果tool是Folder_Tool这样的class，有多个参数
                for para in tool.tool_parameters:
                    self.tool_descs += '\t{'

                    self.tool_descs += '\t参数名称: ' + para['name'] + ',\n'
                    self.tool_descs += '\t\t参数类型: ' + para['type'] + ',\n'
                    self.tool_descs += '\t\t参数描述: ' + para['description'] + ',\n'
                    self.tool_descs += '\t\t参数是否必需: ' + para['required'] + ',\n'

                    self.tool_descs += '\t},'
            else:
                # 如果tool是folder_agent_as_tool这样的实例，只有1个"自然语言指令"参数
                self.tool_descs += '\t{'

                self.tool_descs += '\t参数名称: ' + '自然语言指令' + ',\n'
                self.tool_descs += '\t\t参数类型: ' + 'string' + ',\n'
                self.tool_descs += '\t\t参数描述: ' + '本参数即为交给本工具的指令，由于是将agent当做tool用，因此输入自然语言指令即可' + ',\n'
                self.tool_descs += '\t\t参数是否必需: ' + 'True' + ',\n'

                self.tool_descs += '\t},'

            self.tool_descs += '\n]\n\n'

        self.tool_names = ','.join(self.tool_names)

        # self.agent_tools_description_and_full_history = self. agent_tools_description_and_full_history.format(tool_descs=self.tool_descs, tool_names=self.tool_names, query=self.query)

        return self

    def save_agent_tools_description_and_full_history_to_file(self, answer_this_turn):
        dblue()
        dblue(f'final answer(turn {self.turns_num})'.center(80, '='))
        dblue(answer_this_turn)
        dblue(f'/final answer(turn {self.turns_num})'.center(80, '-'))

        print(f'/thinking(turn {self.turns_num})'.center(80, '-'))

        with open("agent_tools_description_and_full_history.txt", "w", encoding="utf-8") as file:
            file.write(self.agent_tools_description_and_full_history)

    def get_final_answer(self):
        return self.final_answer

    def _parse_final_answer(self, answer):
        # self.__finished_keyword = '最终答复'
        # 去掉'[最终答复]'及之前的内容
        self.final_answer = answer.split(f'[{self.__finished_keyword}]')[-1]
        # print(f'self.final_answer已解析，final answer关键字"{self.__finished_keyword}"已去除.')

    def clear_history(self):
        # 设置为第一次query，相当于清楚历史
        self.first_query = True

    # 每一次run之前都要正确设置状态
    def _run_before(self):
        # 完全初始化Agent_Status
        self.status = Agent_Status()
        self.status.started = True

    # 每一次run之后都要正确设置状态
    def _run_after(self, success):
        self.status.finished = True
        self.status.task_success = success


    def run(self,
            query=None,
            context:Query_Agent_Context=None,
            in_max_retry=config.Agent.MAX_TRIES
            ):
        self._run_before()
        try:
            self.current_query = query or self.query

            # -----------------------根据query获取experience(agent_as_tool时不提供经验)-------------------------
            if self.tool_description is None and self.exp:
                self.current_exp_str = self.exp.query_agent_experience_by_task_info(agent_task_info_string=self.current_query)
                dyellow(f'----------------------agent查询经验(agent_id="{self.agent_id}")--------------------------------')
                dyellow(f'用户query: {self.current_query!r}')
                dyellow(f'根据query查询到的关联经验: {self.current_exp_str!r}')
                dyellow(f'---------------------/agent查询经验(agent_id="{self.agent_id}")--------------------------------')
            # ----------------------/根据query获取experience-------------------------------------------------

            if self.first_query or (not self.has_history):
                # 第一次query 或者 没有history
                self.first_query = False

                self.agent_tools_description_and_full_history = PROMPT_REACT.format(
                    tool_descs=self.tool_descs,
                    tool_names=self.tool_names,
                    query=self.current_query,
                    user_experience=self.current_exp_str,
                )
            else:
                # 有history，且不是first query
                self.agent_tools_description_and_full_history += f'\n<用户问题>\n{self.current_query}\n</用户问题>\n'

            dblue(f'config.Agent.MAX_TRIES = {in_max_retry}')
            for i in range(in_max_retry):
                if self.is_canceling(): break

                # 1、思考
                answer_this_turn = self.thinking()
                # dred(f'-------------tool_just_outputed = "{self.tool_paras_just_outputed}"----------------------')
                # if (self.__finished_keyword in answer_this_turn) and (self.tool_paras_just_outputed==False):    # 同时要求tool_paras_just_outputed为False才意味着结束，是用于避免刚输出tool参数、还没调用tool并观察结果，就因为输出了[最终答复]直接退出、没调用工具。
                #     self._parse_final_answer(answer_this_turn)
                #     return True
                if self.is_canceling(): break

                # 2、行动
                action_result = self.action(in_answer=answer_this_turn, context=context)
                if self.is_canceling(): break

                # 如输出[最终答复]且无tool，则表明任务完成，正常退出
                dred(f'-------------tool_just_outputed = "{self.tool_paras_just_outputed}"----------------------')
                if (self.__finished_keyword in answer_this_turn) and (self.tool_paras_just_outputed==False):    # 同时要求tool_paras_just_outputed为False才意味着结束，是用于避免刚输出tool参数、还没调用tool并观察结果，就因为输出了[最终答复]直接退出、没调用工具。
                    self.save_agent_tools_description_and_full_history_to_file(answer_this_turn)
                    self._parse_final_answer(answer_this_turn)

                    # --------------总结经验(agent_as_tool时不总结经验)--------------
                    if self.tool_description is None and self.exp:
                        dyellow(f'----------------------本次agent执行得到的经验(agent_id="{self.agent_id}")------------------------')
                        self.exp.summarize_agent_history(agent_history_string=self.agent_tools_description_and_full_history)
                        dyellow(f'"{self.exp.get_all_exp_string()}"')
                        dyellow(f'---------------------/本次agent执行得到的经验(agent_id="{self.agent_id}")------------------------')
                    # -------------/总结经验------------------------------------------
                    dgreen(f'--------------------已获得[最终答复]且无tool调用，正常退出.----------------------------')

                    # ----------------run()结束-------------------
                    self._run_after(success=True)
                    # self.status.finished = True
                    return True
                    # ---------------/run()结束-------------------

                # 3、观察
                self.observation(in_action_result=action_result)
                if self.is_canceling(): break

                dred(f'-------------tool_just_outputed to "False"----------------------')
                self.tool_paras_just_outputed = False   # 防止正常[最终答复]环节时，都无法退出(用于避免刚输出tool参数、还没调用tool并观察结果，就因为输出了[最终答复]直接退出、没调用工具。)

            if self.is_canceling():
                self.set_canceled()

            self.final_answer = '未能成功答复，请重试。'
            # ----------------run()结束-------------------
            self._run_after(success=False)
            # self.status.finished = True
            return False
            # ---------------/run()结束-------------------
        except Exception as e:
            dred('-------------------------------Tool_Agent.run()报错------------------------------------')
            dred(f'{e!r}')
            dred('------------------------------/Tool_Agent.run()报错------------------------------------')
            return False

    def _thoughts_stream_output(self, gen):
        # self._start_time = time.time()

        thoughts = ''
        thoughts_copy_to_print = ''

        # stream输出
        str_last_turn = ''
        for chunk in gen:
            if self.is_canceling(): break

            # chunk = chunk[2]

            thoughts +=chunk

            dgreen(chunk, end='', flush=True)

            thoughts_copy_to_print +=chunk
            if f'[{self.__finished_keyword}]' in thoughts:
                # 最终结果stream输出(去除'[最终答复]'这些字)
                # if self.ostream_use_chunk:
                # 采用chunk输出，chunk = string_this_turn - string_last_turn
                str_this_turn = thoughts.split(f'[{self.__finished_keyword}]')[-1]  # 去除'[最终答复]'这些字

                # --------------------------写入queue stream-----------------------------
                self.stream_queues.final_answer.put(str_this_turn.split(str_last_turn)[-1] if str_last_turn != '' else str_this_turn)
                # -------------------------/写入queue stream-----------------------------

                # dyellow(f'-----> "{str_this_turn}"')
                # if self.output_stream_to_console:
                #     # 输出到console
                #     self.output_result_stream_chunk(
                #         str_this_turn.split(str_last_turn)[-1] if str_last_turn != '' else str_this_turn ,
                #         end='',
                #         flush=True
                #     )
                # else:
                #     # 输出到如word文档中
                #     self.output_result_stream_chunk(str_this_turn.split(str_last_turn)[-1] if str_last_turn != '' else str_this_turn)
                #     # self.thinking_stream_chunk( str_this_turn.split(str_last_turn)[-1] if str_last_turn != '' else str_this_turn )
                str_last_turn = str_this_turn
                # else:
                    # 采用full_string输出
                    # --------------------------写入queue stream-----------------------------
                    # self.stream_queues.final_answer.put(thoughts.split(f'[{self.__finished_keyword}]')[-1])
                    # self.stream_queues.final_answer.put(GeneratorDone)
                    # -------------------------/写入queue stream-----------------------------

                    # self.output_result_stream_full_string(thoughts.split(f'[{self.__finished_keyword}]')[-1])    # 去除'[最终答复]'这些字
                    # self.output_stream(chunk, thoughts.replace(self.__finished_keyword, ''))
            else:
                # --------------------------写入queue stream-----------------------------
                self.stream_queues.output.put(chunk)
                # -------------------------/写入queue stream-----------------------------

                # self.output_thinking_stream_chunk(chunk)
                # 中间状态stream输出(streamlit的status不支持stream输出，所以这里为空操作，并在后续作status_print处理)
                # self.status_stream(chunk, thoughts)

                # 注意：这里必须是'\n\n'，和agent输出有关，如果是'\n'就会导致页面上额外输出了一行
                if '\n\n' in thoughts_copy_to_print:
                    # 输出已经有\n的内容
                    print_content = thoughts_copy_to_print.split('\n\n')[0]
                    # self.status_print(print_content)
                    # if self.status_list is not None:
                    #     self.status_list.append(print_content)
                    # 删除第一个\n前的内容
                    l = thoughts_copy_to_print.split('\n\n')
                    l.pop(0)
                    thoughts_copy_to_print = '\n\n'.join(l)    # 这里用' '.join而不用'\n'.join是为了防止streamlit中status.markdown额外输出\n
        dgreen()
        # --------------------------写入queue stream-----------------------------
        # self.stream_queues.output.put(GeneratorDone)
        # self.stream_queues.final_answer.put(GeneratorDone)
        # -------------------------/写入queue stream-----------------------------

        # stream输出最后的end
        # if self.ostream_end_func:
        #     self.ostream_end_func()

        # 添加输出历史
        if self.__finished_keyword in thoughts:
            # 最终结果输出历史
            if self.output_list is not None:
                self.output_list.append(thoughts.split(f'[{self.__finished_keyword}]')[-1])    # 去除'[最终答复]'这些字
                # self.output_list.append(thoughts.replace(self.__finished_keyword, ''))
        else:
            # 中间状态输出历史
            # self.status_print(thoughts) # streamlit的status无法stream输出，只能这里print输出

            pass
            # if self.status_list is not None:
            #     self.status_list.append(thoughts)

        # self._end_time = time.time()
        # dyellow(f"【action拿到tool_name的执行时间: {self._end_time - self._start_time:.4f} 秒】")
        return thoughts

    def thinking(self):
        # dyellow('-----------------------------------thinking------------------------------------')
        # dyellow(self.agent_tools_description_and_full_history)
        # dyellow('----------------------------------/thinking------------------------------------')
        self.turns_num += 1
        print(f'thinking(turn {self.turns_num})'.center(80, '='))
        # print(f'原始his: {self.agent_desc_and_action_history}', flush=True)
        dred(f'manual_stop: "{self.response_stop}"')

        query = LLM_Query_Paras(
            query=self.agent_tools_description_and_full_history,
            manual_stop=self.response_stop
        )
        self.llm.ask_prepare(query)
        # self.llm.ask_prepare(
        #     self.agent_tools_description_and_full_history,
        #     # stop=self.response_stop,  # vllm的stop（如['观察']）输出有问题，所以暂时作专门处理
        #     manual_stop = self.response_stop,
        # )

        think_gen = self.llm.get_think_generator()
        for ch in think_gen:
            # --------------------------写入queue stream-----------------------------
            self.stream_queues.thinking.put(ch)
            # -------------------------/写入queue stream-----------------------------
        # self.stream_queues.thinking.put(GeneratorDone)

        # gen = self.llm.ask_prepare(self.agent_desc_and_action_history, in_stop=self.action_stop).get_answer_generator()
        # thoughts = ''

        result_gen = self.llm.get_result_generator()
        dred(f'-----------------self._thoughts_stream_output-0----------------------')
        # dyellow(f'text: "{self.agent_tools_description_and_full_history}"')
        answer_this_turn = self._thoughts_stream_output(result_gen)
        dred(f'answer_this_turn = {answer_this_turn}')
        dred(f'-----------------self._thoughts_stream_output-1----------------------')

        # gen = self.llm.ask_prepare(
        #     self.agent_tools_description_and_full_history,
        #     # stop=self.response_stop,  # vllm的stop（如['观察']）输出有问题，所以暂时作专门处理
        #     manual_stop = self.response_stop,
        # ).get_answer_generator()
        #
        # answer_this_turn = self._thoughts_stream_output(gen)



        if self.is_canceling():
            self.agent_tools_description_and_full_history += '\n<用户中断>用户中断了执行。</用户中断>'
            return '<用户中断>用户中断了执行。</用户中断>'

        # dyellow('-----------------------------------thinking answer------------------------------------')
        # dyellow(answer_this_turn)
        # dyellow('----------------------------------/thinking answer------------------------------------')
        if not answer_this_turn.strip():
            import sys
            dyellow('-----------------------------------thinking answer-------------------------------------------')
            dred('answer_this_turn完全为空，请检查大模型的api是否有问题（如官网deepseek r1模型会出现回复为空的情况、vllm推理GPT-oss模型也有该情况）。程序退出！')
            dyellow('-----------------------------------thinking answer-------------------------------------------')
            sys.exit(1)

        if self.turns_num == 1:
            with open("../answer(turn 1).txt", "w", encoding="utf-8") as file:
                file.write(answer_this_turn)

        self.agent_tools_description_and_full_history += '\n' + answer_this_turn

        print(f'/thinking(turn {self.turns_num}, {self.llm.get_history_input_tokens_num()}tokens, id={self.agent_id})'.center(80, '-'))
        return answer_this_turn

    def action(self, in_answer, context:Query_Agent_Context=None):
        try:
            dgreen(f'action(turn {self.turns_num})'.center(80, '='))
            # --------------------------- call tool ---------------------------
            action_result = ''

            # print(f'in_answer1: {in_answer}')
            # 去掉'[观察]'及后续内容
            in_answer = in_answer.split('[观察]')
            if len(in_answer)>1:
                in_answer.pop()
            in_answer = ''.join(in_answer)
            # print(f'in_answer2: {in_answer}')
            tool_name = Base_Tool.extract_tool_name_from_answer(in_answer)
            if isinstance(tool_name, list) and (self.__finished_keyword in in_answer):
                # 注意：LLM有时候输出[最终答复]时，仍会调用工具，此时调用工具是正确做法。
                # 因此这里，要解决有[最终答复]、没有工具(即工具调用报错)的问题
                action_result = in_answer
                dgreen(f'/action(turn {self.turns_num})'.center(80, '-'))
                return action_result
            elif isinstance(tool_name, str):
                # 返回是string，正常
                # print(f'=============================thoughts=============================')
                # print(in_thoughts)
                # print(f'-----------------------------thoughts-----------------------------')
                dblue(f'【tool_name: "{tool_name}"】'.center(40, '-'))

                if self.registered_tool_instances_dict.get(tool_name):
                    dred(f'-------------tool_just_outputed changed to "True"----------------------')
                    self.tool_paras_just_outputed = True    # 用于避免刚输出tool参数、还没调用tool并观察结果，就因为输出了[最终答复]直接退出、没调用工具。

                    # # 如果有tool输出，则去掉[最终答复]及后续内容，因为tool还没调用，此时最终输出肯定不对
                    # in_answer = in_answer.split(f'[{self.__finished_keyword}]')
                    # if len(in_answer) > 1:
                    #     in_answer.pop()
                    # in_answer = ''.join(in_answer)

                    # 解析tool_paras
                    # dict_string = legacy_extract_dict_string(in_answer)
                    # dict = json5.loads(dict_string)
                    dict = extract_tool_dict(in_answer)
                    callback_tool_paras_dict = dict['tool_parameters']

                    # 调用工具前，创建tool_ctx(生成tool_task_id，并用于存放后续可能的dataset_info)
                    tool_ctx = create_tool_ctx()

                    # 获取上一个工具的调用结果tool_context
                    last_tool_ctx = None
                    if self.last_tool_task_id is not None:
                        last_tool_ctx = get_tool_ctx(self.last_tool_task_id)

                    # 调用工具
                    # from pprint import pprint
                    print('---------------------------------agent调用tool时的参数情况：self.registered_tool_instances_dict------------------------------------')
                    print(self.registered_tool_instances_dict)
                    print('--------------------------------/agent调用tool时的参数情况：self.registered_tool_instances_dict------------------------------------')
                    # rtn = self.registered_tool_instances_dict[tool_name].call(
                    #     callback_tool_paras_dict=callback_tool_paras_dict,  # 将agent生成的调用tool的参数传给tool
                    #     callback_agent_config=self.agent_config,            # 将agent配置传给tool
                    #     callback_agent_id=self.agent_id,                    # 将agent_id传给tool
                    #     callback_last_tool_ctx=last_tool_ctx,               # 上一个tool的上下文context(包含tool_task_id和可能的dataset_info)
                    #     callback_father_agent_exp=self.current_exp_str      # 调用agent_as_tool时，将经验exp传给该agent_as_tool
                    # )

                    # ---------------------线程化、可cancel，主要针对agent_as_tool、复杂tool等长过程---------------------
                    rtn = None
                    tool_class_or_agent = self.registered_tool_instances_dict[tool_name]
                    def _run_tool_call_thread():
                        dred(f'-------------------------tool线程启动(agent_id="{self.agent_id}")------------------------------')
                        dred(f'tool_name: {tool_name!r}')
                        dred(f'callback_tool_paras_dict: {callback_tool_paras_dict!r}')
                        dred(f'self.agent_config: {self.agent_config!r}')
                        dred(f'self.top_agent_id: {self.top_agent_id!r}')
                        dred(f'self.agent_id: {self.agent_id!r}')
                        dred(f'last_tool_ctx: {last_tool_ctx!r}')
                        dred(f'self.current_exp_str: {self.current_exp_str!r}')
                        dred(f'------------------------/tool线程启动(agent_id="{self.agent_id}")------------------------------')

                        tool_call_paras = Tool_Call_Paras(
                            callback_top_agent_id=self.top_agent_id,
                            callback_tool_paras_dict=callback_tool_paras_dict,
                            callback_agent_config=self.agent_config,
                            callback_agent_id=self.agent_id,
                            callback_last_tool_ctx=last_tool_ctx,
                            callback_client_ctx=context,
                            callback_father_agent_exp=self.current_exp_str
                        )
                        rtn = tool_class_or_agent.call(tool_call_paras)
                        # --------------------------写入queue stream-----------------------------
                        self.stream_queues.tool_rtn_data.put(tool_call_paras)
                        # -------------------------/写入queue stream-----------------------------

                        # rtn = tool_class_or_agent.call(
                        #     callback_tool_paras_dict=callback_tool_paras_dict,  # 将agent生成的调用tool的参数传给tool
                        #     callback_agent_config=self.agent_config,            # 将agent配置传给tool
                        #     callback_agent_id=self.agent_id,                    # 将agent_id传给tool
                        #     callback_last_tool_ctx=last_tool_ctx,               # 上一个tool的上下文context(包含tool_task_id和可能的dataset_info)
                        #     callback_father_agent_exp=self.current_exp_str      # 调用agent_as_tool时，将经验exp传给该agent_as_tool
                        # )
                        dred(f'--------------------------tool线程运行完毕(agent_id="{self.agent_id}", top_agent_id="{self.top_agent_id}")------------------------------')
                        dred(f'rtn: {rtn!r}')
                        dred(f'-------------------------/tool线程运行完毕(agent_id="{self.agent_id}", top_agent_id="{self.top_agent_id}")------------------------------')

                        # 这里返回rtn很关键，不然就要用nonlocal rtn才行，局域内的rtn变量并不是外层rtn，这个一定要注意
                        # 然后后续用rtn = future.result()获取结果
                        return rtn

                    future = g_thread_pool_executor.submit(_run_tool_call_thread)

                    # wait线程，直到结束或cancel信息
                    while not future.done():
                        if self.is_canceling():
                            dyellow('--------------------------工具调用成功cancel----------------------------------')
                            # upper agent
                            dyellow(f'upper agent_id="{self.agent_id}"')

                            #lower agent
                            if not isinstance(tool_class_or_agent, type):
                                # 如果是agent instance，而不是Tool Class
                                # dred(f'self obj: "{self}", agent_id="{self.agent_id}"')
                                # dred(f'tool_class_or_agent obj: "{tool_class_or_agent}", agent_id="{tool_class_or_agent.agent_id}"')
                                tool_class_or_agent.set_cancel()
                                dyellow(f'lower agent_as_tool agent_id="{tool_class_or_agent.agent_id}"')

                            dyellow('-------------------------/工具调用成功cancel----------------------------------')
                            break

                        time.sleep(0.5)
                    # --------------------/线程化、可cancel，主要针对agent_as_tool、复杂tool等长过程---------------------
                    # dred(f'--------------------------tool线程运行完毕1(agent_id="{self.agent_id}")------------------------------')
                    rtn = future.result()
                    # dred(f'--------------------------tool线程运行完毕2(agent_id="{self.agent_id}")------------------------------')
                    # dred(f'rtn = {rtn!r}')
                    # dred(f'-------------------------/tool线程运行完毕2(agent_id="{self.agent_id}")------------------------------')

                    if isinstance(rtn, Action_Result):
                        # local返回的是Action_Result对象
                        pass
                    else:
                        # remote返回的是Action_Result对象对应的dict
                        rtn = Action_Result(**rtn)

                    # 更新tool的上下文context
                    update_tool_context_info(
                        tool_ctx,
                        # action_result=rtn.result,
                        data_set_info=rtn.data_set_info
                    )

                    # dred(f'--------------------------tool线程运行完毕2(agent_id="{self.agent_id}")------------------------------')

                    # 控制台输出action_result
                    dblue(f'rtn: "{rtn}"')
                    dblue(f'action_result: "{rtn.result}"')

                    # dred(f'--------------------------tool线程运行完毕3(agent_id="{self.agent_id}")------------------------------')

                    # 更新last_tool_task_id
                    self.last_tool_task_id = tool_ctx.tool_info.tool_task_id

                    action_result=rtn.result
                else:
                    # self.status_print('未选择任何工具。')
                    pass
                # --------------------------- call tool ---------------------------

                # self.status_print(f'调用工具的行动结果为: \n{action_result}')
                # self.output_log_stream_chunk(f'\n调用工具的行动结果为: \n{action_result}\n')

                # dblue(f'action_result(turn {self.turns_num})'.center(80, '='))
                # dblue(action_result)
                # dblue(f'/action_result(turn {self.turns_num})'.center(80, '-'))

                dgreen(f'/action(turn {self.turns_num})'.center(80, '-'))
                return action_result
            elif isinstance(tool_name, list):
                # 返回了list，是['error', 'error info']这样的结构
                if tool_name[0]=='error':
                    error_info = tool_name[1]
                    dred(error_info)
                    action_result = error_info
                    return action_result
        except Exception as e:
            dred('-------------------------------Tool_Agent.action()报错------------------------------------')
            dred(f'{e!r}')
            dred('------------------------------/Tool_Agent.action()报错------------------------------------')
            return None

    def observation(self, in_action_result=''):
        self.agent_tools_description_and_full_history += '\n' + f'[观察]{in_action_result}'

        # dcyan(f'==============================full_history(turn {self.turns_num})=======================')
        # dcyan(self.agent_tools_description_and_full_history)
        # dcyan(f'-----------------------------/full_history(turn {self.turns_num})-----------------------')

        # with open("agent_tools_description_and_full_history.txt", "w", encoding="utf-8") as file:
        #     file.write(self.agent_tools_description_and_full_history)

        # print(f'============================prompt start============================\n')
        # print(f'{self.prompt}\n------------------------prompt end------------------------')

# client第二步：调用某些tool组合的agent
def client_run_agent(query:str, agent_config:Agent_Config, tool_names:List[str]):
    class_list = get_all_registered_tools_class(tool_names)
    # class_list = legacy_get_all_local_tools_class(tool_names)
    agent = Tool_Agent(
        query='当前目录下有哪些文件',
        tool_classes=class_list,
        agent_config=agent_config
    )
    agent.init()
    success = agent.run()

def main():
    from agent.tools.search_tool import Search_Tool
    tools=[Search_Tool, Url_Content_QA_Tool]
    # tools=[Search_Tool, Code_Tool, Energy_Investment_Plan_Tool, QA_Url_Content_Tool]

    # tools=[Code_Tool]
    # print(tools)
    exit = False
    cont = False
    while True:
        print("请输入多行信息并以Ctrl+D确认，或输入'exit'结束：")
        query = ''
        lines = []
        while True:
            try:
                line = input()
                if line.strip()=='exit':
                    exit = True
                    break
                lines.append(line)
            except EOFError:
                query = '\n'.join(lines)
                if query.strip()=='':
                    # 输入为空
                    cont = True
                    
                break
        if exit:
            break
        if cont:
            cont = False
            continue
            
        agent = Tool_Agent(query=query, tool_classes=tools)
        agent.init()
        success = agent.run()
        if success:
            dblue(f"\n[运行结果]成功。")
        else:
            dred(f"\n[运行结果]失败，请进一步优化问题的描述。")

def main2():
    from agent.tools.search_tool import Search_Tool
    tools=[Search_Tool]
    query = '搜索网络告诉我莱温斯基是谁？'
    agent = Tool_Agent(query=query, tool_classes=tools)
    agent.init()
    success = agent.run()
    if success:
        dblue(f"\n[运行结果]成功。")
    else:
        dred(f"\n[运行结果]失败，请进一步优化问题的描述。")
    print(f'最终答复:')
    print(agent.get_final_answer())

def main_folder():
    import config
    from agent.core.tool_agent import Tool_Agent
    from agent.tools.folder_tool import Folder_Tool
    from agent.core.agent_config import Agent_Config
    from agent.tools.tool_manager import server_register_all_local_tool_on_start
    from agent.tools.tool_manager import get_all_registered_tools_class

    print(f'os: "{config.get_os()}"')
    if config.get_os()=='windows':
        query = r'请告诉我"file_to_find.txt"在"d:\demo\"文件夹的哪个具体文件夹中'
        # query = r'请告诉我"file_to_find.txt"在"y:\demo\"文件夹的哪个具体文件夹中'
    else:
        query = r'我叫土土，请告诉我"file_to_find.txt"在"/home/tutu/demo/"文件夹的哪个具体文件夹中，要仔细搜索其子文件夹。'
        # query = r'我叫土土，请告诉我"./"文件夹里有哪些文件，不作任何解释，直接输出结果'

    tools=[Folder_Tool]
    config = Agent_Config(
        tool_names=['Folder_Tool'],
        # llm_config=llm_protocol.g_online_groq_kimi_k2
        # llm_config=llm_protocol.g_local_gpt_oss_20b_mxfp4
        # llm_config=llm_protocol.g_online_groq_gpt_oss_20b
        llm_config=llm_protocol.g_online_groq_gpt_oss_120b
        # llm_config=llm_protocol.g_local_qwen3_4b_thinking

        # llm_config=llm_protocol.g_local_qwen3_30b_chat
        # llm_config=llm_protocol.g_local_qwen3_30b_thinking
    )

    # server_register_all_local_tool_on_start()
    # get_all_registered_tools_class()


    agent = Tool_Agent(
        has_history=True,
        tool_classes=tools,
        agent_config=config
    )
    agent.init()
    success = agent.run(query=query)
    dyellow(f'最终输出：\n{agent.final_answer}')
    # success = agent.run(query='我刚才告诉你我叫什么？并且告诉我"file_to_find.txt"在"/home/tutu/demo/"文件夹的哪个具体文件夹中。')
    # dyellow(f'最终输出：\n{agent.final_answer}')

    # agent.clear_history()
    # success = agent.run(query='我刚才告诉你我叫什么？并且告诉我"/home/tutu/demo"下有哪些文件夹')
    # dyellow(f'history cleared. 最终输出：\n{agent.final_answer}')

def main_table():
    import config
    from agent.core.tool_agent import Tool_Agent
    from agent.tools.table_tool import Table_Tool
    from agent.core.agent_config import Agent_Config

    tools=[Table_Tool]
    # tools=[Folder_Tool, Search_Tool]
    # query = '第一步：搜索"万向创新聚能城"，返回万向创新聚能城所在城市；第二步搜索所在城市，返回该城市概况'
    query=''
    print(f'os: "{config.get_os()}"')
    if config.get_os()=='windows':
        # query = r'请返回y:/demo/负荷及平衡.xlsx里的"负荷预测"标签中的表格数据，不绘制表格'
        query = r'请返回d:/demo/负荷及平衡.xlsx里的"负荷预测"标签中的表格数据，不绘制表格'
    else:
        query = r'请告诉我y:/demo/负荷及平衡.xlsx里的"负荷预测"标签中的表格数据.'

    config = Agent_Config(
        # base_url='http://powerai.cc:28001/v1',  # llama-4-400b#llama-4-400b
        # base_url='http://powerai.cc:28002/v1',  # qwen3-235b
        base_url='https://api.deepseek.com/v1',
        # base_url='http://powerai.cc:38001/v1',   #deepseek-r1-671b
        # base_url='http://powerai.cc:8001/v1',   #qwen3-30b
        # api_key='empty',
        api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
        # model_id='deepseek-reasoner',  # 模型指向 DeepSeek-R1-0528
        llm_model_id='deepseek-chat',     # 模型指向 DeepSeek-V3-0324
    )
    agent = Tool_Agent(
        query=query,
        tool_classes=tools,
        agent_config=config,
    )
    agent.init()
    success = agent.run()

if __name__ == "__main__":
    # main()
    # main2()
    # table_main()

    main_folder()
    # main_table()