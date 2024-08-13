from openai import OpenAI

# 设置api-key和LLM的地址
oai = OpenAI(
    # api_key='empty',
    # base_url='http://172.27.67.106:8001/v1',
    # base_url='http://127.0.0.1:8001/v1',

    # base_url='http://localhost:8001/v1',
    api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
    base_url='https://api.deepseek.com/v1',
)

# 流式输出的调用
def message_stream(gen):
    for chunk in gen:
        if chunk.choices and hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content

def main():
    try:
        # 获取LLM服务器上的具体模型id
        model_id = oai.models.list().data[0].id
        print(f'模型id：{model_id!r}')

        messages = [{'role': 'system','content': 'You are a helpful assistant.'},{'role': 'user','content': '你是谁？'}]

        # 向LLM发送messages
        # mid=model_id
        # mid='deepseek-chat'
        mid='deepseek-coder'
        gen = oai.chat.completions.create(model=mid,temperature=0.7,messages=messages,stream=True,max_tokens=1024,)

        # 流式输出LLM的回复
        for chunk in message_stream(gen):
            print(chunk, end='', flush=True)

    except Exception as e:
        print(f'访问LLM服务器报错：{e}')

if __name__ == '__main__':
    main()




