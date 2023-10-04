import requests
import json

class Wizardcoder_Fastapi_Client():
    def __init__(self,
                 url='http://localhost:8000/stream/',               # 注意：必须为http://或https://开头，否则报错：No connection adapters were found
                 stream_headers = {'Content-Type': 'text/event-stream'},   # 用于接收stream
                 ):
        self.url = url
        self.stream_headers = stream_headers
        self.gen = None

    def ask_prepare(self,
                    message,
                    temperature=0.7,
                    top_p=0.9,
                    top_k=10,
                    repetition_penalty=1.1,
                    max_new_tokens=2048,
                    stop=["</s>"],
                    ):
        body = {
            'message' : message,
            'temperature' : temperature,
            'top_p' : top_p,
            'top_k' : top_k,
            'repetition_penalty' : repetition_penalty,
            'max_new_tokens' : max_new_tokens,
            'stop' : stop,
        }
        data = json.dumps(body)

        print('=================0==================')
        # self.gen = requests.post(url=self.url, data=data).json()
        print('=================1==================')

        response = requests.post(url=self.url, data=body, headers=self.stream_headers, stream=True)
        print(f'res: {response}')
        for chunk in response.iter_content(chunk_size=1024, decode_unicode=True):
            print(chunk)

    def get_answer_and_sync_print(self):
        print('=================2==================')
        if self.gen is None:
            print('请求尚未响应。')
        result = ''
        print('gen is : ', self.gen, flush=True)
        # print('gen is : ', self.gen.data)
        for chunk in self.gen:
            if chunk:
                print(f'chunk1 is : {chunk}', flush=True)
                print(f'chunk2 is : {chunk.decode("utf-8")}', flush=True)
                print(f'chunk3 is : {chunk.decode("utf-8")}', flush=True)
                chunk = json.loads(chunk.decode("utf-8"))
                result += chunk.delta
                print(chunk, end='', flush=True)
        print(flush=True)

        return result

def main():
    llm = Wizardcoder_Fastapi_Client()
    llm.ask_prepare('translate the word "你好" to english')
    # llm.get_answer_and_sync_print()

if __name__ == "__main__" :
    main()


