import gradio as gr

from gpu_server.Openai_Api_for_Qwen import *
from gpu_server.Stable_Diffusion import *

import numpy as np
def flip_image(x):
    print('image: ',x)
    return np.fliplr(x)
def main():
    llm = LLM_Qwen()
    # res = llm.ask("简单描述一下一个女生正在进行某种运动的情形，用英文回复。").sync_print()

    with gr.Blocks() as demo:  # 使用gr.Blocks构建界面

        prompt = gr.Textbox(label="输入框")  # 创建文本输入框
        output = gr.Textbox(label="输出框")  # 创建文本输出框

        greet_btn = gr.Button("聊天")  # 创建按钮控件

        # 为按钮添加点击事件
        # 点击时调用chat函数
        # 输入来自prompt输入框
        # 输出显示到output输出框
        greet_btn.click(fn=lambda x:llm.ask(x).sync_print(), inputs=prompt, outputs=output)

        with gr.Tab("Flip Image"):
            image_button = gr.Button("Flip")
            with gr.Row():
                # image_input = gr.Image()
                image_output = gr.Image()


        image_button.click(fn=lambda x:Stable_Diffusion.quick_get_image('1girl, super model, in library, breasts, wet, extremely sexy, look at viewer, nipples, long legs, full body, beautiful'), inputs=prompt, outputs=image_output)

    demo.launch()  # 启动构建的界面

if __name__ == "__main__":
    main()