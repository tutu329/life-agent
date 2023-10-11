import requests
from requests.exceptions import RequestException
import json

class Wizardcoder_Fastapi_Client():
    def __init__(self,
                 url='http://localhost:8000/stream/',               # 注意：必须为http://或https://开头，否则报错：No connection adapters were found
                 # stream_headers = {'Content-Type': 'text/event-stream'},   # 用于接收stream
                 ):
        self.url = url
        self.gen = None
        # self.stream_headers = stream_headers

    def ask_prepare(self,
                    message,
                    temperature=0.7,
                    top_p=0.9,
                    top_k=10,
                    repetition_penalty=1.1,
                    max_new_tokens=2048,
                    stop=["</s>"],
                    ):
        req = {
            'message' : message,
            'temperature' : temperature,
            'top_p' : top_p,
            'top_k' : top_k,
            'repetition_penalty' : repetition_penalty,
            'max_new_tokens' : max_new_tokens,
            'stop' : stop,
        }

        try:
            # 必须用上面这一行，下面增加headers的这一行报错
            response = requests.post(url=self.url, json=req, stream=True)
            # response = requests.post(url=self.url, json=req, headers=self.stream_headers, stream=True)
            response.raise_for_status()
            self.gen = response
        except RequestException as e:
            print(f'请求服务器出错：{e}')

    def get_answer_and_sync_print(self):
        result = ''
        for chunk in self.gen.iter_content(chunk_size=1024, decode_unicode=True):
            # 返回的chunk格式： 'data: {"delta":"you? ","finish_reason":null}'
            # 需要去掉头上的'data:'
            try:
                chunk_data = json.loads(chunk[5:])
            except json.JSONDecodeError as e:
                print(f'response.iter_content的chunk在json.loads()时报错：{e}')
            print(chunk_data['delta'], end='', flush=True)
            result += chunk_data['delta']
            # print(chunk_data)
        print(flush=True)

        return result
class Phind_Codellama_Fastapi_Client():
    def __init__(self,
                 url='http://localhost:8000/stream/',               # 注意：必须为http://或https://开头，否则报错：No connection adapters were found
                 # stream_headers = {'Content-Type': 'text/event-stream'},   # 用于接收stream
                 ):
        self.url = url
        self.gen = None
        # self.stream_headers = stream_headers

    def ask_prepare(self,
                    message,
                    temperature=0.7,
                    top_p=0.95,
                    top_k=40,
                    repetition_penalty=1.1,
                    max_new_tokens=512,
                    stop=["</s>"],
                    ):
        req = {
            'message' : message,
            'temperature' : temperature,
            'top_p' : top_p,
            'top_k' : top_k,
            'repetition_penalty' : repetition_penalty,
            'max_new_tokens' : max_new_tokens,
            'stop' : stop,
        }

        try:
            # 必须用上面这一行，下面增加headers的这一行报错
            response = requests.post(url=self.url, json=req, stream=True)
            # response = requests.post(url=self.url, json=req, headers=self.stream_headers, stream=True)
            response.raise_for_status()
            self.gen = response
        except RequestException as e:
            print(f'请求服务器出错：{e}')

    def get_answer_and_sync_print(self):
        result = ''
        for chunk in self.gen.iter_content(chunk_size=1024, decode_unicode=True):
            # 返回的chunk格式： 'data: {"delta":"you? ","finish_reason":null}'
            # 需要去掉头上的'data:'
            try:
                chunk_data = json.loads(chunk[5:])
            except json.JSONDecodeError as e:
                print(f'response.iter_content的chunk在json.loads()时报错：{e}')
            print(chunk_data['delta'], end='', flush=True)
            result += chunk_data['delta']
            # print(chunk_data)
        print(flush=True)

        return result

def main_completion():
    llm = Wizardcoder_Fastapi_Client()
    # llm = Wizardcoder_Fastapi_Client(url='http://116.62.63.204:8000/stream/')
    llm.ask_prepare('write a simple poem.', max_new_tokens=50)
    res = llm.get_answer_and_sync_print()
    print('=============================final result is : =============================\n', res)

def main_console_QA():
    # llm = Wizardcoder_Fastapi_Client()
    # llm = Wizardcoder_Fastapi_Client(url='http://116.62.63.204:8000/stream/')
    llm = Phind_Codellama_Fastapi_Client()

    while True:
        question = input('user: ')
        llm.ask_prepare(question, max_new_tokens=512)
        res = llm.get_answer_and_sync_print()

    # while True:
    #     question = input('user: ')
    #     prompt_template = f'''Below is an instruction that describes a task. Write a response that appropriately completes the request.
        ## Instruction:
        # {question}
        ## Response:
        # '''
        # llm.ask_prepare(prompt_template, max_new_tokens=500)
        # res = llm.get_answer_and_sync_print()

if __name__ == "__main__" :
    # main_completion()
    main_console_QA()


