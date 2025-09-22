from openai import OpenAI
import sys

# 设置api-key和LLM的地址
oai = OpenAI(
    base_url='http://powerai.cc:8001/v1',
    api_key='empty',
)

LIGHT_GRAY = '\033[37m'  # 亮灰色
DARK_GREEN = '\033[38;5;22m'  # 深绿色
LIGHT_RED = '\033[91m'  # 明亮红色
RESET = '\033[0m'

def on_user_input(query):
    sys.stdout.write(f'{LIGHT_RED}{query}{RESET}')
    sys.stdout.flush()

def on_reasoning_chunk(chunk):
    sys.stdout.write(f'{LIGHT_GRAY}{chunk}{RESET}')
    sys.stdout.flush()

def on_content_chunk(chunk):
    sys.stdout.write(f'{DARK_GREEN}{chunk}{RESET}')
    sys.stdout.flush()

def parse_stream(gen, on_reasoning_chunk, on_content_chunk):
    """
    单循环分发：将同一个 gen 中的增量区分为 reasoning 与 content 回调。
    on_reasoning/on_content: callable(str)，接收增量文本。
    """
    def _extract_text(node):
        if not node:
            return ""
        if isinstance(node, str):
            return node
        if isinstance(node, dict):
            if isinstance(node.get("content"), str):
                return node["content"]
            if isinstance(node.get("text"), str):
                return node["text"]
            if isinstance(node.get("content"), list):
                return "".join(
                    (p if isinstance(p, str) else (p.get("text") or p.get("content") or ""))
                    for p in node["content"]
                )
        return ""

    reasoning_content = ""
    output_content = ""
    first_output_chunk = True

    on_reasoning_chunk('[reasoning]')
    for chunk in gen:
        choices = getattr(chunk, "choices", None) or []
        if not choices:
            continue
        delta = getattr(choices[0], "delta", None) or {}
        # 推理增量
        reasoning = getattr(delta, "reasoning", None) or (delta.get("reasoning") if isinstance(delta, dict) else None)
        rtxt = _extract_text(reasoning)
        if rtxt:
            on_reasoning_chunk(rtxt)
            reasoning_content += rtxt

        # DeepSeek 类兼容
        thinking = getattr(delta, "thinking", None) or (delta.get("thinking") if isinstance(delta, dict) else None)
        ttxt = _extract_text(thinking)
        if ttxt:
            on_reasoning_chunk(ttxt)
            reasoning_content += ttxt

        # 可见内容增量
        ctxt = getattr(delta, "content", None)
        if ctxt is not None:
            # 官方通常是纯 str；有些实现会给 list/dict，这里只处理 str
            if isinstance(ctxt, str):
                if first_output_chunk:
                    on_content_chunk('\n[content]')
                    first_output_chunk = False

                on_content_chunk(ctxt)
                output_content += ctxt
    print()

def main():
    try:
        # 获取LLM服务器上的具体模型id
        model_id = oai.models.list().data[0].id
        print(f'模型id：{model_id!r}')

        # messages = [{'role': 'system','content': 'You are a helpful assistant.'},{'role': 'user','content': '1+1？'}]
        messages = [
            {'role': 'system','content': 'You are a helpful assistant.'},
        ]

        # 向LLM发送messages
        mid=model_id
        # mid='deepseek-chat'
        # mid='deepseek-coder'

        while True:
            on_user_input('[用户输入]: ')
            prompt = input()
            if prompt == 'exit':
                break
            else:
                messages.append({'role': 'user', 'content': prompt})
                gen = oai.chat.completions.create(model=mid, temperature=0.7, messages=messages, stream=True, max_tokens=1024)

                # 流式输出LLM的回复
                parse_stream(gen, on_reasoning_chunk=on_reasoning_chunk, on_content_chunk=on_content_chunk)

    except Exception as e:
        print(f'访问LLM服务器报错：{e}')

if __name__ == '__main__':
    main()