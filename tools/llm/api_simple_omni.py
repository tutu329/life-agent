# 运行前的准备工作:
# 运行下列命令安装第三方依赖
# pip install numpy soundfile openai

import os
import base64
import io
import wave
import soundfile as sf
import numpy as np
from openai import OpenAI

# 1. 初始化客户端
client = OpenAI(
    api_key=os.getenv("QWEN_API_KEY"),  # 确认已配置环境变量
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

# 2. 发起请求
try:
    messages = [
        {'role': 'system',
         'content': 'You are a professional video game narrative generation engine, specifically designed to create detailed descriptions of environments, characters, plotlines, and other narrative elements within game scenarios.'},
        {'role': 'user',
         'content': '''现在你模拟魔兽世界，当我和你对话时，你用以下格式输出内容：【环境】这里描写环境、角色情况、动作、表情等细节，角色名要用[]括起来，角色名不用每次都重复出现。【对话】这里以某一个角色的身份和我对话。（注意：对话中，不要以故事生成器引擎的身份、不要以旁白的视角、不要以第一人称视角、不要很啰嗦，一定要以第三人称视角，说话内容、风格要和角色吻合，明白了吗，现在我们开始。）'''},
        {'role': 'assistant', 'content': '好的，我明白了，我们现在开始。'},
        # {'role': 'system','content': 'You are a helpful assistant.'},
    ]

    completion = client.chat.completions.create(
        model="qwen3-omni-flash",
        messages=messages,
        modalities=["text", "audio"],  # 指定输出文本和音频
        # audio={"voice": "Nofish", "format": "wav"},
        audio={"voice": "Dylan", "format": "wav"},
        # audio={"voice": "Cherry", "format": "wav"},
        stream=True,  # 必须设置为 True
        stream_options={"include_usage": True},
    )

    # 3. 处理流式响应并解码音频
    print("模型回复：")
    audio_base64_string = ""
    for chunk in completion:
        # 处理文本部分
        if chunk.choices and chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="")

        # 收集音频部分
        if chunk.choices and hasattr(chunk.choices[0].delta, "audio") and chunk.choices[0].delta.audio:
            audio_base64_string += chunk.choices[0].delta.audio.get("data", "")

    # 4. 保存音频文件
    if audio_base64_string:
        wav_bytes = base64.b64decode(audio_base64_string)
        audio_np = np.frombuffer(wav_bytes, dtype=np.int16)
        sf.write("audio_assistant.wav", audio_np, samplerate=24000)
        print("\n音频文件已保存至：audio_assistant.wav")

except Exception as e:
    print(f"请求失败: {e}")