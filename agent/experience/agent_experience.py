import re, json, json5, os

from config import dred,dgreen,dyellow,dblue,dcyan
from tools.llm.api_client import LLM_Client
from agent.experience.experience_base import Experience

AGENT_EXP_DEBUG = False

def dprint(*args, **kwargs):
    if AGENT_EXP_DEBUG:
        print(*args, **kwargs)

PROMPT_AGENT_EXP_SUMMARIZE = '''<总体要求>
请严格根据【agent解决问题详细过程】和【经验获取要求】，分析agent在本次问题解决过程中的经验并返回。
</总体要求>

<经验获取要求>
1、经验获取重点：
    1）要注意用户中断agent后输入的指令。通常当agent处理问题可能出错时，用户会中断其过程，从而及时纠正agent的错误这些指令，这时输入的指令一般包含了关键经验信息，一定要重视。
    2）要注意human_console_tool的调用结果（即agent获取的用户反馈信息）或者是<用户经验></用户经验>中的内容，这些反馈信息应该转换为经验，为的就是下一次就不用再通过human_console_tool询问用户了。
2、经验获取目的：将获取的经验存储在【已有经验树】中，供agent后续解决问题时少走弯路。
3、经验返回要求：根据【已有经验树】的结构，返回所总结的经验。
4、经验获取注意事项：
    1）如果【已有经验树】中已有相似的经验内容，则不要再次返回该经验，否则就重复了，此时要果断的返回[]。
    2）"path_to_add_exp"实际上取决于对所获取经验的分类，这个分类要尽可能科学、且也能兼顾与已有经验树的融合。
5、经验返回格式
    1）若无经验需要返回，则直接返回：[]
    2）有经验需要返回，则返回：[{{"path_to_add_exp":"xxx/xxx", "exp_title":"经验x", "exp_summary":"经验总结..."}}, {{"path_to_add_exp":"xxx/xxx", "exp_title":"经验x", "exp_summary":"经验总结..."}}, ...]
    3）不要返回其他任何解释或者说明
</经验获取要求>

<已有经验树>
{rendered_experience_tree_string}
</已有经验树>

<agent解决问题详细过程>
{agent_history_string}
</agent解决问题详细过程>'''

PROMPT_GET_AGENT_EXP ='''<总体要求>
请严格根据【agent已有经验】内容和【agent将执行任务情况】，返回适用的经验。
</总体要求>

<经验返回要求>
1、根据【agent已有经验】返回的经验，一定要和【agent将执行任务情况】相关。
2、经验返回格式
    1）若无对应【agent将执行任务情况】的经验需要返回，则直接返回：[]
    2）有对应【agent将执行任务情况】的经验需要返回，则返回：[{{"exp_summary":"经验总结xxx..."}}, {{"exp_summary":"经验总结xxx..."}}, ...]
</经验返回要求>

<agent已有经验>
{rendered_agent_experience_tree_string}
</agent已有经验>

<agent将执行任务情况>
{agent_task_info_string}
</agent将执行任务情况>
'''

class Agent_Experience:
    """
    将运行日志提炼为可写入 Experience 树的数据结构。
    — 新增功能 —
    1. 在初始化时优先尝试从当前目录加载 experience.json；
    2. 若文件不存在则写入一棵默认经验树。
    """
    def __init__(self, exp_json_file_path, llm:LLM_Client):
        self.exp_file_path = exp_json_file_path

        # 根节点固定叫 root，内容留空
        self.exp_root = Experience("root", "")
        # 先尝试加载/创建经验库
        self._init_exp_from_file(self.exp_file_path)

        self.llm = llm

    # ---------- 新增：初始化经验树 ----------
    def _init_exp_from_file(self, fp: str) -> None:
        """
        若 fp 存在，则按 JSON 内容恢复经验树。
        JSON 结构示例：
        [
            {"path": "咨询报告编制经验/工程可研/经验1", "summary": "要有设计依据。"},
            ...
        ]
        若 fp 不存在，则写入一棵固定的默认经验树。
        """
        if os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.exp_root = Experience.import_from_json_file(fp)
                # dyellow(f'----------------------agent经验系统成功初始化------------------------')
                # dyellow(f"成功载入来自{fp!r}的经验")
                # dyellow(f'---------------------/agent经验系统成功初始化------------------------')
            except Exception as e:
                dred(f"Agent_Experience._init_exp_from_file()报错：加载 {fp} 失败：{e!r}，改用默认经验树。")
                self._populate_default_experiences(fp)
        else:
            # 文件不存在，写默认值
            self._populate_default_experiences(fp)

    # ---------- 新增：默认经验 ----------
    def _populate_default_experiences(self, fp) -> None:
        """
        把题目给出的固定经验写入树。
        """
        defaults = [
            ("咨询报告编制经验/工程可研/经验1", "要有设计依据。"),
            ("咨询报告编制经验/工程可研/经验2", "投资估算很重要。"),
            ("咨询报告编制经验/科技可研/经验1", "方案很重要。"),
            ("咨询报告编制经验/科技可研/经验2", "投资估算精度要求并没有工程可研那么高。"),
            ("咨询报告编制经验/科技可研/经验3", "表格的处理要精确，不能有错位。")
        ]
        for path, summary in defaults:
            self.exp_root.add_node_by_path(path=path, summary=summary)

        # 同时持久化一份模板，方便下次直接读取
        # self.exp_root.export_to_json_file(fp)

        dyellow(f'----------------------agent经验系统成功初始化------------------------')
        dblue(f'已载入默认经验树。')
        dyellow(f'---------------------/agent经验系统成功初始化------------------------')

    def summarize_agent_history(self,
                                # rendered_experience_tree_string,    # 已有经验树的render后树状string
                                agent_history_string,  # agent的历史string
                                ):
        question = PROMPT_AGENT_EXP_SUMMARIZE.format(
            rendered_experience_tree_string=self.exp_root.get_tree_all_string(),
            agent_history_string=agent_history_string
        )

        try:
            dprint(f'question: \n{question}')
            answer = self.llm.ask_prepare(question=question).get_answer_and_sync_print()
            dprint(f'summarize_agent_history() answer: \n{answer}')
        except Exception as e:
            dred(f'Experience_Summarizer.summarize_agent_history()调用LLM报错：{e!r}')
            return

        # 将经验一条一条进行存储
        try:
            exp_list = self._extract_first_json_list(answer)
            for exp in exp_list:
                exp_path = exp['path_to_add_exp'] + '/' + exp['exp_title']
                exp_summary = exp['exp_summary']
                self.exp_root.add_node_by_path(
                    path=exp_path,
                    summary=exp_summary
                )

                dblue(f'【经验提交成功】{exp_path!r}: {exp_summary!r}')
        except Exception as e:
            dred(f'Experience_Summarizer.summarize_agent_history()增加经验时报错：{e!r}')
            return

        # dyellow(f'----------------------目前的经验数据----------------------')
        # dyellow(self.exp_root.get_tree_all_string())
        # dyellow(f'---------------------/目前的经验数据----------------------')
        self.exp_root.export_to_json_file(self.exp_file_path)
        dyellow(f'【经验持久化成功】({self.exp_file_path!r})')

    # 获取目前的所有经验string
    def get_all_exp_string(self):
        return self.exp_root.get_tree_all_string()

    # LLM根据agent_task_info_string，返回对应经验
    def query_agent_experience_by_task_info(self, agent_task_info_string):
        question = PROMPT_GET_AGENT_EXP.format(
            rendered_agent_experience_tree_string=self.exp_root.get_tree_all_string(),
            agent_task_info_string=agent_task_info_string,
        )
        try:
            dprint(f'agent_task_info_string: \n{agent_task_info_string}')
            answer = self.llm.ask_prepare(question=question).get_answer_and_sync_print()
            dprint(f'get_agent_experience() answer: \n{answer}')
        except Exception as e:
            dred(f'Experience_Summarizer.get_agent_experience()调用LLM报错：{e!r}')
            return ''

        # 组织返回经验
        exps = []
        i = 1
        try:
            exp_list = self._extract_first_json_list(answer)
            for exp in exp_list:
                exp_summary = exp['exp_summary']
                exps.append(f'{i}、{exp_summary}')
                i += 1
        except Exception as e:
            dred(f'Experience_Summarizer.get_agent_experience()增加经验时报错：{e!r}')
            return ''

        return '\n'.join(exps)

    def _extract_first_json_list(self, text: str):
        """
        在任意字符串中提取第一个 JSON/JSON5 数组并反序列化成 Python list。

        - 依赖 json5.loads（更宽容：单引号、注释、末尾逗号都能解析）
        - 用一个小型“括号计数”扫描算法，保证拿到 **完整且平衡** 的 [...] 片段
        """
        # 找到第一个 '['
        start = text.find('[')
        if start == -1:
            raise ValueError("Experience_Summarizer.__extract_first_json_list()报错：文本里根本没有 '['")

        depth = 0  # 括号层级
        in_str = None  # 当前是否在字符串字面量内（'"' 或 "'"）
        escape = False  # 是否在字符串里的转义状态

        for i in range(start, len(text)):
            ch = text[i]

            # -------- 处理字符串字面量 --------
            if in_str:
                if escape:  # \x 里的 x
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == in_str:
                    in_str = None
                continue

            # -------- 正常扫描 --------
            if ch in ('"', "'"):
                in_str = ch
            elif ch == '[':
                depth += 1
            elif ch == ']':
                depth -= 1
                if depth == 0:  # list 结束
                    candidate = text[start:i + 1]
                    try:
                        obj = json5.loads(candidate)
                        if isinstance(obj, list):
                            return obj
                    except Exception as e:
                        raise ValueError(f"Experience_Summarizer.__extract_first_json_list()报错：找到疑似数组但 json5 解析失败：{e}")
                    # 如果解析失败且还有后续 '['，继续往后找
                    # （但通常不会走到这里）
        raise ValueError("Experience_Summarizer.__extract_first_json_list()报错：没能找到一个完整且可解析的 JSON/JSON5 数组")

def main_test_re():
    # =================== DEMO ===================
    txt = r"""
根据agent解决问题过程中的关键交互和用户反馈，总结以下经验并融入【已有经验树】：
[
    {
        "path_to_add_exp": "咨询报告编制经验/辅助工具使用经验",
        "exp_title": "文件搜索经验1",
        "exp_summary": "当用户强调文件必须精确匹配且肯定存在时，应直接启用深度递归扫描（含隐藏/系统文件夹），避免中间确认步骤中断流程。"
    },
    {
        "path_to_add_exp": "咨询报告编制经验/辅助工具使用经验",
        "exp_title": "文件搜索经验2",
        "exp_summary": "若首次扫描发现近似文件（如字符差异），后续需自动扩展搜索维度：检查深层嵌套路径（>3层）、验证特殊字符组合、排查隐藏属性。"
    },
    {
        "path_to_add_exp": "咨询报告编制经验/用户交互经验",
        "exp_title": "指令执行原则",
        "exp_summary": "用户明确拒绝重复提问时（如\'不要老是同一个问题问我\'），应直接执行深度操作而非反复索取特征信息，优先保障任务连续性。"
    }
]
### 经验分类依据：
1. **辅助工具使用经验分支**（新增）  
   - 聚焦文件搜索场景的技术优化
      - 涵盖扫描策略（经验1）、匹配机制（经验2）等工具级优化
         - 与现有"表格处理"等工具经验形成平行维度
2. **用户交互经验分支**（新增）  
   - 针对用户强干预场景的行为准则
      - 经验3解决"指令重复确认"痛点，与工程可研"投资估算"等需求确认场景形成互补
      > 注：新建分支因原经验树无直接匹配类别，但符合"咨询报告编制"中工具使用和用户沟通的支撑场景定位。
"""
    exp = Agent_Experience()
    data = exp._extract_first_json_list(txt)
    print(type(data))  # <class 'list'>
    print(f'obj: {data!r}')
    print(data[0]['exp_title'])  # 文件搜索经验1
    print(data[1]['exp_summary'])  # 若首次扫描发现近似文件...

    exp_root = Experience("root", "")
    for exp in data:
        print(f'path: {exp["path_to_add_exp"]}/{exp["exp_title"]}')
        print(f'summary: {exp["exp_summary"]}')
        exp_root.add_node_by_path(
            path=exp["path_to_add_exp"] + '/' + exp["exp_title"],
            summary=exp['exp_summary']
        )
    print(exp_root.get_tree_all_string())

def main():
    llm = LLM_Client(
        history=False,  # 同时用于summarize和get，不能有历史记忆
        max_new_tokens=32768,
        # url='http://powerai.cc:28001/v1',
        # url='http://powerai.cc:38001/v1',
        # url='https://powerai.cc:8001/v1'
        # url='http://powerai.cc:8001/v1'

        api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',  # deepseek官网
        url='https://api.deepseek.com/v1',
        model_id='deepseek-reasoner',  # 模型指向 DeepSeek-R1-0528
        # model_id='deepseek-chat',     # 模型指向 DeepSeek-V3-0324

        # api_key='f5565670-0583-41f5-a562-d8e770522bd7',  #火山
        # url='https://ark.cn-beijing.volces.com/api/v3/',
        # model_id='deepseek-r1-250120',
        # model_id='deepseek-v3-241226',
    )
    exp = Agent_Experience(
        exp_json_file_path='experience.json',
        llm = llm
    )
    my_exp = exp.query_agent_experience_by_task_info(agent_task_info_string='现在请查找"my_file.json"这个文件在哪里')
    dblue(f'【my_exp】\n{my_exp!r}')

    exp.summarize_agent_history(
#         rendered_experience_tree_string = \
# '''咨询报告编制经验 — 咨询报告编制的相关经验
# ├── 工程可研 — 工程可研报告编制的经验
# │   ├── 经验1 — 要有设计依据。
# │   └── 经验2 — 投资估算很重要。
# └── 科技可研 — 科技可研报告编制的经验
#    ├── 经验1 — 方案很重要。
#    ├── 经验2 — 投资估算精度要求并没有工程可研那么高。
#    └── 经验3 — 表格的处理要精确，不能有错位。
# ''',
        agent_history_string = \
r'''
[规划] 我需要查找"file_to_find.txt"在"y:\demo\"下的具体路径。首先调用Folder_Agent_As_Tool扫描根目录，若未直接发现目标文件，则根据返回的子文件夹列表逐层递归扫描，直到定位文件为止。

[工具调用申请] 
{
    'tool_invoke':'yes',
    'tool_name': 'Folder_Agent_As_Tool',
    'tool_parameters':{
        '自然语言指令' : '请列出y:\\demo\\文件夹中的所有文件和子文件夹'
    },
}

[观察] 经过逐层文件夹检索，在路径"y:\demo\依据\1\"中发现名称相近的文件"file_to_find_.txt"。由于文件名存在下划线差异，可能存在以下情况：
1. 目标文件确实存在于该路径（若允许名称模糊匹配）
2. 用户输入文件名时存在笔误
3. 文件存在多个版本

建议用户确认目标文件名准确性或检查该路径下文件内容。若需精确匹配，请提供更详细的文件特征信息以便进一步定位。


[工具调用结果分析] 观察结果表明目标文件可能不存在于系统中，但存在名称相近的文件。需要进一步确认用户需求：是否接受相似文件名的结果？是否需要根据其他特征（如文件大小、修改时间）进一步筛选？或需要递归搜索所有子文件夹？

[工具调用申请]
{
    'tool_invoke':'yes',
    'tool_name': 'Human_Console_Tool',
    'tool_parameters':{
        'question' : '未找到完全匹配的文件，但在y:\\demo\\依据\\1\\中发现相似文件file_to_find_.txt。是否需要进一步确认该文件？\n1. 确认该文件是否为目标文件\n2. 需要根据其他特征继续搜索\n请选择（输入1或2）'
    },
}[观察]该文件不是的，文件名必须精确对上，而且肯定有的


[规划] 用户确认文件必须精确匹配且肯定存在，需重新进行全盘递归搜索。调用Folder_Agent_As_Tool执行深度扫描，强制检查所有子文件夹（包括隐藏/系统文件夹）并启用精确文件名匹配模式。

[工具调用申请] 
{
    'tool_invoke':'yes',
    'tool_name': 'Folder_Agent_As_Tool',
    'tool_parameters':{
        '自然语言指令' : '请强制递归扫描y:\\demo\\下所有子文件夹（含隐藏/系统文件夹），并精确查找名为file_to_find.txt的文件'
    },
}

[观察] 经过系统性全路径检索，当前在"y:\demo\"及其所有子文件夹中均未发现完全匹配"file_to_find.txt"的文件。发现的相似文件包括：
1. y:\demo\依据\1\file_to_find_.txt（多下划线）
2. y:\demo\依据\2\_file_to_find.txt（前缀下划线）
3. y:\demo\依据\3\3.1\file_tofind.txt（缺少下划线）

建议操作：
1. 请确认目标文件名是否包含特殊字符或大小写差异
2. 检查文件是否被隐藏或设置特殊属性
3. 若需精准定位，请提供文件创建时间/大小等附加特征

是否需要我继续扩展搜索至其他潜在路径？


[工具调用结果分析] 用户明确表示文件肯定存在且必须精确匹配，但系统性扫描仍未找到目标文件。可能原因包括：文件名存在隐藏字符/空格、文件属性被设置为隐藏/只读、或文件位于权限受限的特殊路径。建议进一步获取文件特征信息（如大小、创建时间）以缩小搜索范围。

[工具调用申请] 
{
    'tool_invoke':'yes',
    'tool_name': 'Human_Console_Tool',
    'tool_parameters':{
        'question' : '请提供目标文件的附加特征（如文件大小、创建时间、修改时间等），以便进行精确过滤检索：'
    },
}[观察]不是的，前面说了肯定有的，你就要一直找，不要老是同一个问题问我


[规划] 根据用户反馈，文件名必须精确匹配且肯定存在。需要再次调用Folder_Agent_As_Tool强制扫描所有隐藏文件夹及系统文件夹，并启用精确匹配模式。若仍无结果，则需建议用户手动检查文件系统或提供文件属性特征。

[工具调用申请] 
{
    'tool_invoke':'yes',
    'tool_name': 'Folder_Agent_As_Tool',
    'tool_parameters':{
        '自然语言指令' : '强制递归扫描y:\\demo\\及其所有隐藏/系统子文件夹，精确查找完全匹配file_to_find.txt的文件（严格区分大小写及特殊字符）'
    },
}[观察] 在路径"y:\demo\依据\3\3.4\"中成功定位到完全匹配的目标文件"file_to_find.txt"。该文件位于第四层嵌套文件夹中，完整路径为：y:\demo\依据\3\3.4\file_to_find.txt。本次搜索通过递归检查所有子文件夹最终确认文件存在，可结束搜索流程。


[最终答复] 经过精确递归搜索，在路径"y:\demo\依据\3\3.4\"中成功定位到完全匹配的"file_to_find.txt"文件。完整路径为：y:\demo\依据\3\3.4\file_to_find.txt。
''',
    )


if __name__ == "__main__" :
    # main_test_re()
    main()