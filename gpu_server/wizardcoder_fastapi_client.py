import requests
import json

class Wizardcoder_Fastapi_Client():
    def __init__(self, url='localhost:8000/stream/'):
        self.url = url
        self.gen = None

    def ask_prepare(self, in_question):
        body = {

        }
        data = json.dumps(body)

        self.gen = requests.post(url=self.url, data=data)

    def get_answer_and_sync_print(self):
        result = ''
        for chunk in self.gen:
            result += chunk
            print(chunk, end='', flush=True)
        print()

        return result

def main():
    llm = Wizardcoder_Fastapi_Client()
    llm.ask_prepare('你是谁？')
    llm.get_answer_and_sync_print()

if __name__ == "__main__" :
    main()


