class Status_Base:
    def __init__(self):
        # 用于yield返回状态：
        # status = {
        #     'status_type'         : 'complete/running',         # 对应streamlit中的status.update中的state参数(complete, running)
        #     'canceled'            : False,                      # 整个任务是否canceled
        #     'status_describe'     : '状态描述',                  # 对应streamlit中的status.update
        #     'status_detail'       : '状态细节',                  # 对应streamlit中的status.write或status.markdown
        #     'llms_complete'       : [False ， ...]              # 所有llm的完成状态(False, True)
        #     'llms_full_responses' : [''， ...]                  # 所有llm的返回文本
        # }
        self.status = {}

    def add_status(self):
        pass