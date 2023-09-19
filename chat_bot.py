import gradio as gr

from gpu_server.Openai_Api_for_Qwen import *
from gpu_server.Stable_Diffusion import *

import numpy as np
import copy

llm = LLM_Qwen()
# llm.set_role_prompt('你正在扮演一个女孩，你好笨笨。')

# ============================关于角色提示============================
# 一、你希望llm了解哪些信息：
# 1) where are you based?
# 2) what do you do for work?
# 3) what are your hobbies and interests?
# 4) what subject can you talk about for hours?
# 5) what are some goals you have?
# 二、你希望llm怎样回复：
# 1) how formal or casual should llm be?
# 2) how long or short should responses generally be?
# 3) how do you want to be addressed?
# 4) should llm have opinions on topics or remain neutral?
# ============================关于角色提示============================

def llm_async_ask(message, history):
    # gradio的典型对话格式： [['我叫土土', '你好，土土！很高兴认识你。'], [], []]

    for item in llm.ask_prepare(message).get_answer_generator():
        yield item
    llm.print_history()

def llm_undo():
    print('执行llm_undo()')
    llm.undo()
    llm.print_history()

def llm_retry(history, message):
    print('执行llm_retry()')
    if history is not None and len(history)>0:
        message = history[-1][0]
        history[-1][1] = ""
        for chunk in llm.get_retry_generator():
            history[-1][1] += chunk
            yield history, message
    llm.print_history()

def llm_clear():
    print('执行llm_clear()')
    llm.clear_history()
    llm.print_history()

def llm_answer(history, message):
    print('执行llm_answer()')
    print('message: ',message)
    message = history[-1][0]
    history[-1][1] = ""
    for chunk in llm_async_ask(message, history):
        history[-1][1] += chunk
        yield history, message

def bot_add_text(history, text, role_prompt):
    llm.set_role_prompt(role_prompt)
    history = history + [(text, None)]
    print('text: ',text)
    print('history: ', history)
    return history, gr.update(value="", interactive=False)

def bot_undo(history):
    if history is not None and len(history)>0:
        history.pop()
    print('history: ', history)
    return history, gr.update(value="", interactive=False)

def bot_retry(history, role_prompt):
    llm.set_role_prompt(role_prompt)
    if len(history)>0:
        history[-1][1]=''
    return history, gr.update(value="", interactive=False)

def bot_clear(history):
    if history is not None:
        history.clear()
    print('history: ', history)
    return history, gr.update(value="", interactive=False)

def bot_add_file(history, file):
    history = history + [((file.name,), None)]
    print('history: ', history)
    return history

# def llm_on_role_prompt_change(prompt):
#     llm.set_role_prompt(prompt)

def main():
    with gr.Blocks() as demo:
        chatbot = gr.Chatbot(
            [],
            elem_id="chatbot",
            bubble_full_width=False,
            # avatar_images=(None, (os.path.join(os.path.dirname(__file__), "avatar.png"))),
        )

        with gr.Row():
            user_input = gr.Textbox(
                # lines=3,
                max_lines=20,
                autofocus=True,
                scale=16,
                show_label=False,
                placeholder="输入文本并按回车，或者上传文件",
                container=False,
            )
            upload_btn = gr.UploadButton("📁", scale=1, file_types=["image", "text", "video", "audio"])

        with gr.Row():
            clear_btn = gr.Button(value="清空", scale=1)
            undo_btn = gr.Button(value="回撤", scale=1)
            retry_btn = gr.Button(value="重试", scale=1)
            submit_btn = gr.Button(value="提交", scale=4)

        with gr.Row():
            role_prompt_tbx = gr.Textbox(
                value='',
                lines=3,
                max_lines=20,
                scale=16,
                show_label=False,
                placeholder="输入角色提示语",
                container=False,
            )
        # role_prompt.change(llm_on_role_prompt_change, role_prompt, None)

        undo_btn.click(
            bot_undo,
            [chatbot],
            [chatbot, user_input],
            queue=False
        ).then(
            llm_undo,
            None,
            None
        ).then(
            lambda: gr.update(interactive=True),
            None,
            [user_input],
            queue=False
        )

        retry_btn.click(
            bot_retry,
            [chatbot, role_prompt_tbx],
            [chatbot, user_input],
            queue=False
        ).then(
            llm_retry,
            [chatbot, user_input],
            [chatbot, user_input]
        ).then(
            lambda: gr.update(interactive=True),
            None,
            [user_input],
            queue=False
        )

        clear_btn.click(
            bot_clear,
            [chatbot],
            [chatbot, user_input],
            queue=False
        ).then(
            llm_clear,
            None,
            None
        ).then(
            lambda: gr.update(interactive=True),
            None,
            [user_input],
            queue=False
        )

        submit_btn.click(
            bot_add_text,
            [chatbot, user_input, role_prompt_tbx],
            [chatbot, user_input],
            queue=False
        ).then(
            llm_answer,
            [chatbot, user_input],
            [chatbot, user_input],
        ).then(
            lambda: gr.update(interactive=True),
            None,
            [user_input],
            queue=False
        )

        txt_msg = user_input.submit(
            bot_add_text,
            [chatbot, user_input, role_prompt_tbx],
            [chatbot, user_input],
            queue=False
        ).then(
            llm_answer,
            [chatbot, user_input],
            [chatbot, user_input]
        ).then(
            lambda: gr.update(interactive=True),
            None,
            [user_input],
            queue=False
        )
        file_msg = upload_btn.upload(bot_add_file, [chatbot, upload_btn], [chatbot], queue=False).then(
            llm_answer, [chatbot, user_input], chatbot
        )

    demo.queue().launch()

if __name__ == "__main__":
    main()
