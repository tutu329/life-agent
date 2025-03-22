from openai import OpenAI
import openai

# model = 'v3'
model = 'r1'
# model = 'qwen-72'

# 设置api-key和LLM的地址
if model == 'v3':
    oai = OpenAI(
        api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
        base_url='https://api.deepseek.com/v1',
    )
    model_id = 'deepseek-chat'
elif model == 'r1':
    oai = OpenAI(
        api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
        base_url='https://api.deepseek.com/v1',
    )
    model_id = 'deepseek-reasoner'
elif model == 'qwen-72':
    oai = OpenAI(
        api_key='empty',
        base_url='https://powerai.cc:8001/v1',
    )
    model_id = oai.models.list().data[0].id

def stream(gen):
    reasoning_finished = False
    for chunk in gen:
        if chunk.choices and hasattr(chunk.choices[0].delta, "reasoning_content") and chunk.choices[0].delta.reasoning_content is not None:
            yield reasoning_finished, chunk.choices[0].delta.reasoning_content
        elif chunk.choices and hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content is not None:
            reasoning_finished = True
            yield reasoning_finished, chunk.choices[0].delta.content

def main():
    try:
        messages = [
            {'role': 'system','content': 'You are a helpful assistant.'},
            {'role': 'user','content': '你是谁？'}
        ]

        # 向LLM发送messages
        gen = oai.chat.completions.create(
            model=model_id,
            temperature=0.7,
            messages=messages,
            stream=True,
            max_tokens=1024,
        )

        # 流式输出LLM的思考和回复
        print('-----------------------------思考-----------------------------')
        reasoning_finished_printed = False
        for res in stream(gen):
            reasoning_finished, chunk = res
            if not reasoning_finished:
                print(chunk, end='', flush=True)
            else:
                if not reasoning_finished_printed:
                    print('\n-----------------------------回复-----------------------------')
                    reasoning_finished_printed = True
                print(chunk, end='', flush=True)

    except Exception as e:
        print(f'访问LLM服务器报错：{e}')

if __name__ == '__main__':
    main()