import gradio as gr

from tools.llm.api_client_qwen_openai import *
from tools.t2i.api_client_stable_diffusion import *

import numpy as np


def flip_image(x):
    print('image: ',x)
    return np.fliplr(x)

llm = LLM_Qwen()

def undo():
    print('执行undo()')
    llm.undo()

def retry():
    print('执行retry()')
    llm.get_retry_generator()

def clear():
    print('执行clear()')
    llm.clear_history()

def async_ask(message, history):
    # gradio的典型对话格式： [['我叫土土', '你好，土土！很高兴认识你。'], [], []]

    res = ''

    # # undo
    # if len(llm.external_last_history)-len(history)==1:
    #     print('执行Undo()')
    #     llm.undo()
    # # retry
    # elif len(history)>1 and len(llm.external_last_history)-len(history)==0:
    #     print('执行retry()')
    #     llm.retry()
    # # ask
    # else:
    for item in llm.ask_prepare(message).get_answer_generator():
        res += item
        yield res

    # 保存history(动态放在llm上)
    # llm.external_last_history = history
    llm.print_history()

    # print('message：',message)
    # print('res：',res)
    # print('对话历史：',history)
    # print('[message, res]：', [message, res])
    # his = copy.deepcopy(history)
    # print('对话历史：', his.append([message, res]), flush=True)

g_imgs = []

# 绘制一张图
def get_image(prompt):
    # prompt = "1girl, super model, in library, extremely seductive, butt, breasts, wet, extremely sexy, look at viewer, nipples, long legs, full body, beautiful"
    img=Stable_Diffusion.quick_get_image(prompt)
    # g_imgs.append(img)
    # if len(g_imgs)>100:
    #     g_imgs.pop(0)
    return img
    # return g_imgs

# 重绘一张图
def redraw_image(prompt):
    global g_imgs
    g_imgs.pop()    # 删除最后一张
    img=Stable_Diffusion.quick_get_image(prompt)
    return img

# 更新gallery（image.change())
def images_on_change(img):
    global g_imgs
    print('================img:', img)
    if img is None:
        return g_imgs

    g_imgs.append(img)
    if len(g_imgs)>100:
        g_imgs.pop(0)   # 删除第一张
    return g_imgs

# ClearButton额外需要做的清空工作（清空gallery）
def clear_images():
    global g_imgs
    g_imgs.clear()
    return g_imgs

def summary(file_obj):
    return 'ok'
    #
def main():
    global g_imgs

    # res = llm.ask("简单描述一下一个女生正在进行某种运动的情形，用英文回复。").sync_print()

    # 图片
    image_output = gr.Image(scale=1, height=600)
    # 图集
    gallery_output = gr.Gallery(preview=True, scale=1, height=600, show_download_button=False)
    # 绘图按钮
    image_button = gr.Button(value="生成")
    # 重绘按钮
    redraw_button = gr.Button(value="重绘")

    with gr.Blocks() as demo:  # 使用gr.Blocks构建界面
        # 为按钮添加点击事件
        # 点击时调用chat函数
        # 输入来自prompt输入框
        # 输出显示到output输出框
        # greet_btn.click(fn=ask, inputs=prompt, outputs=output)
        # greet_btn.click(fn=lambda x:llm.ask(x).sync_print(), inputs=prompt, outputs=output)

        with gr.Tab("生成图片"):
            with gr.Column():
                image_output.render()
                with gr.Row():
                    # 清空按钮
                    clear_button = gr.ClearButton(value="清空", components=[image_output, gallery_output])
                    redraw_button.render()
                    image_button.render()

                gallery_output.render()
                # image_input = gr.Image()
                # image_output = gr.Image(width=512, height=768)
                # gallery_output = gr.Gallery(preview=True, width=512, height=768, show_download_button=False)
                # gallery_output = gr.Gallery(columns=10, rows=10)


        # 绘图指令
        sd_prompt = gr.Textbox(label="输入框", lines=5, value='1girl, super model, in library, extremely seductive, butt, breasts, wet, extremely sexy, look at viewer, nipples, long legs, full body, beautiful')  # 创建文本输入框

        # 重绘按钮
        redraw_button.click(fn=redraw_image, inputs=sd_prompt, outputs=image_output)
        # 绘图按钮
        image_button.click(fn=get_image, inputs=sd_prompt, outputs=image_output)

        # 图片更新
        image_output.change(fn=images_on_change, inputs=image_output, outputs=gallery_output)
        # 图片清空
        clear_button.click(fn=clear_images, inputs=None, outputs=gallery_output)

        # llm_btn = gr.Button("聊天")  # 创建按钮控件

        # file_input = gr.components.File(label="上传文件")
        # file_button = gr.Button("总结文档")
        # file_output = gr.Textbox(label="输出框")  # 创建文本输出框
        # file_button.click(fn=summary, inputs=file_input, outputs=file_output)
    demo.queue().launch()   # 队列模式
def main1():
    submit_btn = gr.Button(value="提交")
    retry_btn = gr.Button(value="重试")
    undo_btn = gr.Button(value="撤回")
    clear_btn = gr.Button(value="清空")
    with gr.Blocks() as demo:  # 使用gr.Blocks构建界面
        ci = gr.ChatInterface(fn=async_ask,  submit_btn=submit_btn,  retry_btn=retry_btn, undo_btn=undo_btn, clear_btn=clear_btn)
        # retry_btn.click(fn=retry(), inputs=None, outputs=None)
        # undo_btn.click(fn=undo(), inputs=None, outputs=None)
        # clear_btn.click(fn=clear(), inputs=None, outputs=None)

    demo.queue().launch()

if __name__ == "__main__":
    main1()
