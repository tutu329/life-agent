# 关于购买deepseek的API
#     1、https://www.deepseek.com/，进入API开放平台
#     2、注册登录、充值如10元
#     3、API keys中“创建API key”，随便取个名字，“复制”，就取得了"sk-xxx"这种形式的api key，保存好，丢失了再创建一个就行。
# 关于使用deepseek的API(初始化OpenAI对象时)
#     1、base_url='https://api.deepseek.com/v1'
#     2、api_key='sk-xxx'
# 关于使用deepseek的API(调用chat.completions.create()时)
#     1、model='deepseek-chat'   # 或者'deepseek-reasoner'
#     2、temperature=0.6         # 0表示生成答案固定，1.0表示生成答案多变
#     3、max_tokens=4096         # 能生成的最大token数量
#     4、stream=True             # 是否流式输出

# 关于购买qwen的API
#     1、https://dashscope.console.aliyun.com，进入API平台
#     2、注册登录、充值如10元
# 关于使用qwen的API(初始化OpenAI对象时)
#     1、base_url='https://dashscope.aliyuncs.com/compatible-mode/v1'
#     2、api_key='sk-xxx'
# 关于使用qwen的API(调用chat.completions.create()时)
#     1、model='qwen3-next-80b-a3b-instruct'
#     2、temperature=0.7         # 0表示生成答案固定，1.0表示生成答案多变
#     3、max_tokens=4096         # 能生成的最大token数量
#     4、stream=True             # 是否流式输出

from openai import OpenAI

# 设置api-key和LLM的地址
oai = OpenAI(
    base_url='http://powerai.cc:8001/v1',
    api_key='empty',
)

# 获取流式输出的接口
def message_stream(gen):
    for chunk in gen:
        if chunk.choices and hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content

def main():
    try:
        # 获取LLM服务器上的模型列表，并取第一个模型的id
        model_id = oai.models.list().data[0].id

        # 或者直接指定模型的id
        mid=model_id
        # mid='deepseek-chat'
        # mid='deepseek-reasoner'

        print(f'模型id：{model_id!r}')

        messages = [
            {'role': 'system','content': 'You are a helpful assistant.'},
        ]

        while True: # 对话循环
            prompt = input('[用户输入]')    # 从控制台获取用户输入
            if prompt == 'exit':
                break
            else:
                messages.append({'role': 'user', 'content': prompt})    # 将用户输入放入对话历史
                gen = oai.chat.completions.create(model=mid, temperature=0.7, messages=messages, stream=True, max_tokens=1024)  # 从LLM api获取模型输出接口

                # 流式输出LLM的回复
                output = ''
                print('[LLM输出]')
                for chunk in message_stream(gen):       # 流式输出LLM返回的内容
                    print(chunk, end='', flush=True)    # 打印流式输出的每一个片段
                    output += chunk                     # 将每一个片段连接起来，组成最终的完整回复
                messages.append({'role': 'assistant','content': output})    # 将llm输出放入对话历史
                print()

    except Exception as e:
        print(f'访问LLM服务器报错：{e}')

if __name__ == '__main__':
    main()