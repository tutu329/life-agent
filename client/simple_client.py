from openai import OpenAI
import openai

# model = 'v3'
model = 'qwen-72'

# 设置api-key和LLM的地址
if model == 'v3':
    oai = OpenAI(
        api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
        base_url='https://api.deepseek.com/v1',
    )
    model_id = 'deepseek-chat'
elif model == 'qwen-72':
    oai = OpenAI(
        api_key='empty',
        base_url='https://powerai.cc:8001/v1',
    )
    model_id = oai.models.list().data[0].id     # 直接用model列表中的第一个（本地部署时，经常只在一个IP:Port上运行一个model）

def stream(gen):
    '''
    从API返回的generator生成器对象中解析chunk内容（generator是python的一种可迭代对象，便于遍历其中元素）
    '''
    for chunk in gen:
        if chunk.choices and hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content

def main():
    try:
        messages = [
            {'role': 'system','content': 'You are a helpful assistant.'},
            {'role': 'user','content': '你是谁？'}
        ]

        # 向LLM发送messages，并返回generator生成器对象
        gen = oai.chat.completions.create(
            model=model_id,
            temperature=0.7,
            messages=messages,
            stream=True,
            max_tokens=1024,
        )

        # 流式输出LLM的回复
        print('-----------------------------回复-----------------------------')
        for chunk in stream(gen):
            print(chunk, end='', flush=True)

    except Exception as e:
        print(f'访问LLM服务器报错：{e}')

if __name__ == '__main__':
    main()
    print('ok')