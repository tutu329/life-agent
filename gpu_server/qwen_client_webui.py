import gradio as gr
import asyncio

from tools.llm.api_client_qwen_openai import *
from tools.doc.llm_doc import *
from tools.retriever.search import search, search_gen, Bing_Searcher

llm = LLM_Qwen(
    need_print=False,
    # temperature=0,
)
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

class Shared():
    internet = False

    @staticmethod
    def set_internet(flag):
        Shared.internet = flag
        print(f'Shared.internet: {Shared.internet}')

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


internet_search_finished = False
internet_search_result = []
def llm_answer(history, message, progress=gr.Progress()):
    print('---------------------执行llm_answer()---------------------')
    message = history[-1][0]
    if '上传文件' in history[-1][0]:
        filename = history[-1][0][0]
        # if 'docx' in filename:
        #     print(f'上传了文件: {history[-1][0][0]}')
        #     history[-1][1] = "" # history[-1][1]即为bot的输出
        #     doc = LLM_Doc(filename)
        #     doc.parse_all_docx()
        #     toc = doc.get_toc_md_string()
        #     history[-1][1] += toc
        #     print(toc)
        #     yield history, ''
    else:
        if current_file != '' and 'docx' in current_file:
            # -----------------已有docx文件上传----------------
            doc = LLM_Doc(current_file)
            doc.llm.need_print = False
            doc.parse_all_docx()
            toc = doc.get_toc_md_for_tool_by_node(doc.doc_root)
            print(f'-----------------------toc----------------------------------')
            print(f'{toc}')
            # tables = doc.get_all_tables()
            tool = doc.llm_classify_question(message)
            answer_gen = doc.call_tools(tool, message, toc, in_tables=None)
            print('user: ', message)
            history[-1][1] = ""
            print('assistant: ', end='')
            for chunk in answer_gen:
                history[-1][1] += chunk
                print(chunk, end='', flush=True)
                yield history, message
            print()
        elif current_file != '' and 'pdf' in current_file:
            # -----------------已有pdf文件上传----------------
            doc = LLM_Doc(current_file)
            doc.llm.need_print = False
            doc.parse_all_pdf()
            toc = doc.get_toc_md_for_tool_by_node(doc.doc_root)
            print(f'-----------------------toc----------------------------------')
            print(f'{toc}')
            # tables = doc.get_all_tables()
            tool = doc.llm_classify_question(message)
            answer_gen = doc.call_tools(tool, message, toc)
            # answer_gen = doc.call_tools(tool, message, toc, tables)
            print('user: ', message)
            history[-1][1] = ""
            print('assistant: ', end='')
            for chunk in answer_gen:
                history[-1][1] += chunk
                print(chunk, end='', flush=True)
                yield history, message
            print()
        elif Shared.internet==False:
            # -----------------不搜索网络----------------
            print('user: ',message)
            history[-1][1] = ""
            print('assistant: ', end='')
            for chunk in llm_async_ask(message, history):
                history[-1][1] += chunk
                print(chunk, end='', flush=True)
                yield history, message
            print()
        elif Shared.internet==True:
            # -----------------搜索网络----------------
            print('user: ',message)
            history[-1][1] = ""
            print('assistant: ', end='')

            # for res in progress.tqdm(search_gen(message), desc='正在调用搜索引擎中...'):
            #     print(f'-----------------------------"{res}"-------------------------------')
            #     if type(res) is not str:
            #         results = res



            global internet_search_finished
            global internet_search_result
            internet_search_finished = False
            internet_search_result = []

            async def _show_progress():
                for i in progress.tqdm(range(100), desc='正在调用搜索引擎中...'):
                    await asyncio.sleep(0.1)
                    if internet_search_finished:
                        print('----------------------------1--------------------------------')
                        break

            async def _search():
                async with Bing_Searcher() as searcher:
                    global internet_search_finished
                    global internet_search_result
                    internet_search_result = await searcher.query_bing_and_get_results(message)
                    internet_search_finished = True
                    print('----------------------------2--------------------------------')
                    print(f'results 2: {internet_search_result}')

            async def await_taks():
                t1 = asyncio.create_task(_show_progress())
                t2 = asyncio.create_task(_search())
                await asyncio.wait([t1, t2])

            loop = asyncio.new_event_loop()
            loop.run_until_complete(await_taks())

            print('----------------------------3--------------------------------')
            print(f'results: {internet_search_result}')

            # tasks = []
            # for url in urls:
            #     tasks.append(asyncio.create_task(self._func_get_one_page(self.context, url)))
            #
            # await asyncio.wait(tasks, timeout=10)

            # progress.tqdm(results, desc='返回搜索内容并分析...')

            url_idx = 0
            for url, content_para_list in internet_search_result:
                # -------------界面上生成一个url对应的内容-------------
                content = " ".join(content_para_list)
                if len(content) < 5000:
                    url_idx += 1

                    prompt = f'这是网络搜索结果: "{content}", 请根据该搜索结果用中文回答用户的提问: "{message}"，回复要简明扼要、层次清晰、采用markdown格式。'
                    temp_llm = LLM_Qwen(history=False)
                    gen = temp_llm.ask_prepare(prompt).get_answer_generator()

                    for chunk in gen:
                        history[-1][1] += chunk     # 输出llm结果
                        print(chunk, end='', flush=True)
                        yield history, message
                    # history[-1][1] += f'\n## &nbsp; '  # 输出空行
                    # yield history, message

                    print(f'\n\n出处[{url_idx}]: ' + url + '\n\n')
                    history[-1][1] += f'\n#### 出处[{url_idx}]: ' + url + '\n## &nbsp; \n## &nbsp; ' # 输出url
                    yield history, message

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

current_file = ''
def bot_on_upload(history, file):
    global current_file
    current_file = file.name
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
            height=500,
            # avatar_images=(None, (os.path.join(os.path.dirname(__file__), "avatar.png"))),
        )

        with gr.Row():
            user_input = gr.Textbox(
                lines=5,
                max_lines=20,
                autofocus=True,
                scale=32,
                show_label=False,
                placeholder="输入文本并按回车，或者上传文件",
                container=False,
            )
            with gr.Column(scale=1, min_width=80):
                internet_cbx = gr.Checkbox(value=False, label="联网", min_width=80)
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


        with gr.Accordion("高级设置", open=False):
        # with gr.Row():
            role_prompt_tbx = gr.Textbox(
                value='',
                lines=10,
                max_lines=20,
                # scale=16,
                show_label=False,
                placeholder="输入角色提示语",
                container=False,
            )
        # role_prompt.change(llm_on_role_prompt_change, role_prompt, None)

        internet_cbx.change(
            fn=Shared.set_internet,
            inputs=internet_cbx,
        )

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

        file_msg = upload_btn.upload(bot_on_upload, [chatbot, upload_btn], [chatbot], queue=False)

        # file_msg = upload_btn.upload(bot_on_upload, [chatbot, upload_btn], [chatbot], queue=False).then(
        #     llm_answer, [chatbot, user_input], [chatbot, user_input]
        # )

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

    demo.queue().launch(server_name='0.0.0.0')

if __name__ == "__main__":
    main()
