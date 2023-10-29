import gradio as gr

from tools.llm.api_client_qwen_openai import *
from tools.doc.llm_doc import *

llm = LLM_Qwen(need_print=False)
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
    print('---------------------执行llm_answer()---------------------')
    message = history[-1][0]
    if '上传文件' in history[-1][0]:
        filename = history[-1][0][0]
        if 'docx' in filename:
            print(f'上传了文件: {history[-1][0][0]}')
            history[-1][1] = "" # history[-1][1]即为bot的输出
            doc = LLM_Doc(filename)
            doc.parse_all_docx()
            node = doc.find_doc_root('2.1.6.3')
            text = []
            doc.get_text_from_doc_node(text, node)
            for line in text:
                history[-1][1] += line + '\n'
                yield history, ''
    else:
        print('user: ',message)
        history[-1][1] = ""
        print('assistant: ', end='')
        for chunk in llm_async_ask(message, history):
            history[-1][1] += chunk
            print(chunk, end='', flush=True)
            yield history, message
        print()

def bot_add_text(history, text, role_prompt):
    llm.set_role_prompt(role_prompt)
    history = history + [(text, None)]
    print('bot add text: ',text)
    print("bot's history: ", history)
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

def bot_on_upload(history, file):
    history = history + [((file.name,'上传文件'), None)]
    print('bot_on_upload, history: ', history)
    return history

# def llm_on_role_prompt_change(prompt):
#     llm.set_role_prompt(prompt)

from typing import Iterable
from gradio.themes.utils import colors, fonts, sizes
from gradio.themes.default import Default
class Qwen_Theme(Default):
    def __init__(
        self,
        *,
        primary_hue: colors.Color | str = colors.emerald,
        secondary_hue: colors.Color | str = colors.blue,
        neutral_hue: colors.Color | str = colors.gray,
        spacing_size: sizes.Size | str = sizes.spacing_sm,
        radius_size: sizes.Size | str = sizes.radius_sm,
        text_size: sizes.Size | str = sizes.text_sm,
        font: fonts.Font
        | str
        | Iterable[fonts.Font | str] = (
            fonts.GoogleFont("Quicksand"),
            "ui-sans-serif",
            "sans-serif",
        ),
        font_mono: fonts.Font
        | str
        | Iterable[fonts.Font | str] = (
            fonts.GoogleFont("IBM Plex Mono"),
            "ui-monospace",
            "monospace",
        ),
    ):
        super().__init__(
            primary_hue=primary_hue,
            secondary_hue=secondary_hue,
            neutral_hue=neutral_hue,
            spacing_size=spacing_size,
            radius_size=radius_size,
            text_size=text_size,
            font=font,
            font_mono=font_mono,
        )

qwen_theme = Qwen_Theme()
def main():
    # gr.themes.builder()
    # pass
    with gr.Blocks(theme=qwen_theme) as demo:
        chatbot = gr.Chatbot(
            [],
            elem_id="chatbot",
            # layout='panel',
            # layout='bubble',
            show_copy_button=True,
            # line_breaks = False,
            # render_markdown=False,
            bubble_full_width=False,
            height=550,
            # avatar_images=(None, (os.path.join(os.path.dirname(__file__), "avatar.png"))),
        )

        with gr.Row():
            user_input = gr.Textbox(
                lines=3,
                max_lines=20,
                autofocus=True,
                scale=32,
                show_label=False,
                placeholder="输入文本并按回车，或者上传文件",
                container=False,
            )
            submit_btn = gr.Button(value="提交", min_width=50, scale=1)

        with gr.Row():
            dark_mode_btn = gr.Button(
                "💡",
                scale=1,
                size="sm",
                min_width=20,
                variant="primary",
            )
            upload_btn = gr.UploadButton(
                "📁",
                scale=1,
                size='sm',
                min_width=20,
                file_types=["image", "text", "video", "audio"],
                # file_count = "multiple"
            )
            undo_btn = gr.Button(value="回撤", min_width=20,scale=3)
            retry_btn = gr.Button(value="重试",min_width=20, scale=3)
            clear_btn = gr.Button(value="清空", min_width=20,scale=6)


        with gr.Row():
            role_prompt_tbx = gr.Textbox(
                value='',
                lines=3,
                max_lines=20,
                # scale=16,
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
        file_msg = upload_btn.upload(bot_on_upload, [chatbot, upload_btn], [chatbot], queue=False).then(
            llm_answer, [chatbot, user_input], [chatbot, user_input]
        )

        dark_mode_btn.click(
            None,
            None,
            None,
            _js="""() => {
            if (document.querySelectorAll('.dark').length) {
                document.querySelectorAll('.dark').forEach(el => el.classList.remove('dark'));
            } else {
                document.querySelector('body').classList.add('dark');
            }
        }""",
            api_name=False,
        )

    demo.queue().launch()

if __name__ == "__main__":
    main()
