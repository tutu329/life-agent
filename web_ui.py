import gradio as gr

from gpu_server.Openai_Api_for_Qwen import *
from gpu_server.Stable_Diffusion import *

import numpy as np
def flip_image(x):
    print('image: ',x)
    return np.fliplr(x)

llm = LLM_Qwen()
def ask(prompt):
    res = ''
    # llm.ask(prompt).sync_print()
    for item in llm.ask(prompt).get_generator():
        res += item
        yield res

g_imgs = []
def get_image(prompt):
    # prompt = "1girl, super model, in library, extremely seductive, butt, breasts, wet, extremely sexy, look at viewer, nipples, long legs, full body, beautiful"
    img=Stable_Diffusion.quick_get_image(prompt)
    # g_imgs.append(img)
    # if len(g_imgs)>100:
    #     g_imgs.pop(0)
    return img
    # return g_imgs

def get_images(img):
    global g_imgs
    g_imgs.append(img)
    if len(g_imgs)>100:
        g_imgs.pop(0)
    return g_imgs

def clear_images():
    global g_imgs
    g_imgs = []
    return

def summary(file_obj):
    return 'ok'
    #
def main():
    global g_imgs

    # res = llm.ask("简单描述一下一个女生正在进行某种运动的情形，用英文回复。").sync_print()

    with gr.Blocks() as demo:  # 使用gr.Blocks构建界面

        # output = gr.Textbox(label="输出框", lines=10)  # 创建文本输出框

        # greet_btn = gr.Button("聊天")  # 创建按钮控件

        # 为按钮添加点击事件
        # 点击时调用chat函数
        # 输入来自prompt输入框
        # 输出显示到output输出框
        # greet_btn.click(fn=ask, inputs=prompt, outputs=output)
        # greet_btn.click(fn=lambda x:llm.ask(x).sync_print(), inputs=prompt, outputs=output)

        with gr.Tab("生成图片"):
            with gr.Row():
                # image_input = gr.Image()
                image_output = gr.Image(width=512, height=768)
                gallery_output = gr.Gallery(preview=True)
                # gallery_output = gr.Gallery(columns=10, rows=10)
            with gr.Row():
                clear_button = gr.Button("清空")
                image_button = gr.Button("生成")

        # image_button.click(fn=lambda x:Stable_Diffusion.quick_get_image('power system'), inputs=prompt, outputs=image_output)
        prompt = gr.Textbox(label="输入框", lines=5,
                            value='1girl, super model, in library, extremely seductive, butt, breasts, wet, extremely sexy, look at viewer, nipples, long legs, full body, beautiful')  # 创建文本输入框
        image_button.click(fn=get_image, inputs=prompt, outputs=image_output)

        image_output.change(fn=get_images, inputs=image_output, outputs=gallery_output)
        clear_button.click(fn=clear_images, inputs=None, outputs=gallery_output)


        # file_input = gr.components.File(label="上传文件")
        # file_button = gr.Button("总结文档")
        # file_output = gr.Textbox(label="输出框")  # 创建文本输出框
        # file_button.click(fn=summary, inputs=file_input, outputs=file_output)


    demo.queue().launch()   # 队列模式

def main1():
    import time
    import gradio as gr

    def slow_echo(message, history):
        for i in range(len(message)):
            time.sleep(0.05)
            yield "You typed: " + message[: i + 1]

    demo = gr.ChatInterface(slow_echo).queue()

    if __name__ == "__main__":
        demo.launch()


if __name__ == "__main__":
    main()
