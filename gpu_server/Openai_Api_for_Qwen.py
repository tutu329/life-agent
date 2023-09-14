import openai
# openai.api_base = "http://powerai.cc:8000/v1"
# openai.api_base = "http://localhost:8000/v1"
openai.api_base = "http://116.62.63.204:8000/v1"
openai.api_key = "none"
from copy import deepcopy

class LLM_Qwen():
    def __init__(self, history=True, history_max_turns=20, history_clear_method='pop'):
        self.gen = None     # 返回结果的generator

        # 记忆相关
        self.history_list = []
        self.history = history
        self.history_max_turns = history_max_turns
        self.history_turn_num_now = 0

        self.history_clear_method = history_clear_method     # 'clear' or 'pop'

        self.question_last_turn = ''
        self.answer_last_turn = ''

        self.role_prompt = ''


    # 动态修改role_prompt
    def set_role_prompt(self, in_role_prompt):
        if in_role_prompt=='':
            return

        self.role_prompt = in_role_prompt
        if self.history_list!=[]:
            self.history_list[0] = {"role": "user", "content": self.role_prompt}
            self.history_list[1] = {"role": "assistant", "content": '好的，我明白了，现在就开始，我会严格按照要求来。'}
        else:
            self.history_list.append({"role": "user", "content": self.role_prompt})
            self.history_list.append({"role": "assistant", "content": '好的，我明白了，现在就开始，我会严格按照要求来。'})

    def __history_add_last_turn_msg(self):
        if self.history and self.question_last_turn!='' :
            question = {"role": "user", "content": self.question_last_turn}
            answer = {"role": "assistant", "content": self.answer_last_turn}
            self.history_list.append(question)
            self.history_list.append(answer)
            if self.history_turn_num_now < self.history_max_turns:
                self.history_turn_num_now += 1
            else:
                if self.history_clear_method=='pop':
                    print('======记忆超限，记录本轮对话、删除首轮对话======')
                    if self.role_prompt!='':
                        self.history_list.pop(2)
                        self.history_list.pop(2)
                    else:
                        self.history_list.pop(0)
                        self.history_list.pop(0)
                elif self.history_clear_method=='clear':
                    print('======记忆超限，清空记忆======')
                    self.__history_clear()

    def __history_clear(self):
        self.history_list.clear()
        self.set_role_prompt(self.role_prompt)
        self.history_turn_num_now = 0

    def __history_messages_with_question(self, in_question):
        msg_this_turn = {"role": "user", "content": in_question}
        if self.history:
            msgs = deepcopy(self.history_list)
            msgs.append(msg_this_turn)
            return msgs
        else:
            return [msg_this_turn]

    def print_history(self):
        print('\n\t================对话历史================')
        for item in self.history_list:
            print(f"\t {item['role']}: {item['content']}")
        print('\t=======================================')

    # 返回stream(generator)
    def ask(self, in_question):
        self.__history_add_last_turn_msg()

        msgs = self.__history_messages_with_question(in_question)
        # print('msgs: ', msgs)
        gen = openai.ChatCompletion.create(
            model="Qwen-7B",
            messages=msgs,
            stream=True,
            max_tokens=2048,
            # Specifying stop words in streaming output format is not yet supported and is under development.
        )
        self.gen = gen

        self.question_last_turn = in_question
        return self

    # 方式1：直接输出结果
    def sync_print(self):
        result = ''
        for chunk in self.gen:
            if hasattr(chunk.choices[0].delta, "content"):
                print(chunk.choices[0].delta.content, end="", flush=True)
                result += chunk.choices[0].delta.content
                # yield chunk.choices[0].delta.content

        print()
        self.answer_last_turn = result
        return result

    # 方式2：返回generator，在合适的时候输出结果
    def get_generator(self):
        answer = ''
        for chunk in self.gen:
            if hasattr(chunk.choices[0].delta, "content"):
                # print(chunk.choices[0].delta.content, end="", flush=True)
                answer += chunk.choices[0].delta.content
                yield chunk.choices[0].delta.content

        self.answer_last_turn = answer

def main():
    llm = LLM_Qwen(history=True, history_max_turns=20, history_clear_method='pop')

    prompt = '不管发你什么，都直接翻译为英文，不解释。'
    llm.set_role_prompt(prompt)

    while True:
        question = input("user: ")
        # llm.ask(question).sync_print()
        for chunk in llm.ask(question).get_generator():
            print(chunk, end='', flush=True)
        llm.print_history()

def main1():
    # from Util_Doc import *
    doc = Document('/Volumes/public/mbp15/mbp15_工作/===智慧能源====/200、===================科技项目===================/2023-08-07-LLM在能源电力系统咨询中的实战应用研究/南麂岛离网型微网示范工程-总报告.docx')
    table_content = []
    table = doc.tables[45]
    for i, row in enumerate(table.rows):
        text = [cell.text for cell in row.cells]
        table_content.append('\n'.join(text))
        print(text)
        # print(tuple(text))

    table_content = '\n'.join(table_content)
    print(table_content)

    llm = LLM_Qwen()
    question = f"你是电力系统专家，请总结这个表格'{table_content}' 的内容，并返回markdown格式的结果"
    print("user: ", question)
    print("Qwen: ", end='')
    llm.ask(question).sync_print()

    # llm = LLM_Qwen()
    #
    # doc = Document('/Volumes/public/mbp15/mbp15_工作/===智慧能源====/200、===================科技项目===================/2023-08-07-LLM在能源电力系统咨询中的实战应用研究/南麂岛离网型微网示范工程-总报告.docx')
    # topic = '投资概算'
    # # topic = '建设规模'
    #
    # count_str = Text_Topic_Search(doc, topic).count()
    #
    # # question = f"请总结这段话：'{text}' 中关于建设规模的内容，去掉无关的内容"
    # question = f"你是电力系统专家，请总结这段话：'{count_str}' 中关于'{topic}'的内容，去掉与'{topic}'无关的内容，并返回markdown格式的结果"
    # print("user: ", question)
    # print("Qwen: ", end='')
    #
    # # -----------------------------直接输出-------------------------------
    # llm.ask(question).sync_print()






    # s_t = Epdi_Text()
    # s_t.init("/Volumes/public/mbp15/mbp15_工作/===智慧能源====/200、===================科技项目===================/2023-08-07-LLM在能源电力系统咨询中的实战应用研究/LLM测试文档.docx")
    # gen = s_t.get_paragraphs_generator_for_docx_file()
    # for para in gen:
    #     # print('段落: ', para)
    #     if '建设规模' in para:
    #         print("content: ", para)
    #
    #         # llm = LLM_Qwen()
    #         # text = para
    #         # background = '你正在协助我校核文档内容，你根据我的问题只以json格式数据的方式回复我，现在我开始提问题了，'
    #         # question = background + f"请问这段文字'{text}' " + "是否与电力工程建设规模相关（请注意，建设规模必须与主变台数、主变容量、间隔扩建情况、线路长度或线路截面之一有关）？如果与电力工程建设规模相关，绝对不要做任何解释，直接返回\{'sucess':True, 'content':text\}, 其中text为你对建设规模内容的总结文字；如果与电力工程建设规模无关，绝对不要做任何解释，直接返回\{'sucess':False, 'content':''\} "
    #         # llm.ask(question).sync_print()


    # ==============================================================================================================
    # llm = LLM_Qwen()
    #
    # text = '2.10.1 工程建设规模 1）新建薄刀咀光伏-沈家湾1回线，新建线路长度0.62km，采用截面为630mm2的电缆。2）扩建沈家湾变110kV间隔1个，进线电缆截面考虑630mm2。2.10.2 110kV主接线 本工程投产后，沈家湾变110kV母线接线维持不变。薄刀咀光伏电站110kV采用线变组接线。2.10.3 电气计算结论 薄刀咀光伏电站接入系统后，电网潮流分布合理，电压质量良好；电网发生故障且能正常切除的情况下，系统能够保持稳定，变电所各级电压满足规程规定；相关厂站短路电流均在其开关设备的额定遮断容量之内。'
    # question = f"请总结这段话：'{text}' 中，关于建设规模的内容"
    # # question = f"我正在校核报告内容，请问这段文字'{text}'，是否是关于电力工程建设规模的描述？"
    # print("user: ", question)
    #
    # print("Qwen: ", end='')
    #
    # # -----------------------------直接输出-------------------------------
    # llm.ask(question).sync_print()

    # -----------------------------获取gen输出-------------------------------
    # gen = llm.ask("你好").get_generator()
    # for chunk in gen:
    #     print(chunk, end='', flush=True)

    # ==============================================================================================================


if __name__ == "__main__" :
    main()

# create a request activating streaming response
# for chunk in openai.ChatCompletion.create(
#     model="Qwen-7B",
#     messages=[
#         {"role": "user", "content": "在'游戏'、'看书'、'旅游'、'吃喝'、'玩乐'、'健身'、'思考'中随机选择一个"}
#     ],
#     max_tokens=1024,
#     stream=True,
#     # Specifying stop words in streaming output format is not yet supported and is under development.
# ):
#     if hasattr(chunk.choices[0].delta, "content"):
#         print(chunk.choices[0].delta.content, end="", flush=True)

# create a request not activating streaming response
# response = openai.ChatCompletion.create(
#     model="Qwen-7B",
#     messages=[
#         {"role": "user", "content": "在'游戏'、'看书'、'旅游'、'吃喝'、'玩乐'、'健身'、'思考'中随机选择一个"}
#     ],
#     stream=False,
#     stop=[] # You can add custom stop words here, e.g., stop=["Observation:"] for ReAct prompting.
# )
# print(response.choices[0].message.content)