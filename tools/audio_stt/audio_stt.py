# 安装：pip install -U openai-whisper
# win的包管理工具choco的安装(管理员模式打开powershell，然后运行)：Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
# 依赖安装ffmpeg(管理员模式打开powershell，可能需要开梯子）：choco install ffmpeg(ffmpeg不安装，会报错：FileNotFoundError: [WinError 2] 系统找不到指定的文件。)
# 网页：https://github.com/openai/whisper

import whisper
from dataclasses import dataclass, field
from config import dred,dgreen,dblue
from singleton import singleton
import os

@dataclass
class Model_Name:
    BASE: str = 'base'
    SMALL: str = 'small'
    MEDIUM: str = 'medium'

@singleton
class AudioSTT:
    def __init__(self, model_name:Model_Name=Model_Name.MEDIUM):
        self._model_name = model_name
        self._model = None
        self._inited = False

    def _init(self):
        if self._inited==True:
            return

        if self._model is None:
            try:
                self._model = whisper.load_model(self._model_name)
                self._inited = True
            except Exception as e:
                self._model = None
                dred(f'AudioSTT模型加载失败: "{e}"')
            dgreen(f'AudioSTT模型加载成功, 模型类型为"{self._model_name}".')

    def stt(self, file_name):
        self._init()

        if self._model is None:
            dred(f'AudioSTT模型尚未加载, stt()返回为空.')
            return ''

        audio = whisper.load_audio(file_name)
        audio = whisper.pad_or_trim(audio)
        mel = whisper.log_mel_spectrogram(audio).to(self._model.device)
        _, probs = self._model.detect_language(mel)
        options = whisper.DecodingOptions()
        result = whisper.decode(self._model, mel, options)
        return result.text

def _legacy_stt_demo(in_mp3_filename, in_model='base'):
    # model = whisper.load_model("medium")
    # model = whisper.load_model("small")
    # model = whisper.load_model("base")
    model = whisper.load_model(in_model)

    # load audio and pad/trim it to fit 30 seconds
    # print('当前文件夹: ', os.getcwd())
    audio = whisper.load_audio(in_mp3_filename)
    # audio = whisper.load_audio("output.mp3")
    audio = whisper.pad_or_trim(audio)

    # make log-Mel spectrogram and move to the same device as the model
    mel = whisper.log_mel_spectrogram(audio).to(model.device)

    # detect the spoken language
    _, probs = model.detect_language(mel)
    # print(f"Detected language: {max(probs, key=probs.get)}")

    # decode the audio
    options = whisper.DecodingOptions()
    result = whisper.decode(model, mel, options)

    # print the recognized text
    # print(result.text)
    return result.text


def main():
    # res = stt('C:\\Users\\tutu\\Downloads\\你是谁.m4a', in_model='medium')
    # # res = stt('/tools/output.mp3', in_model='medium')
    # print('语音所包含文字为：', res)

    for i in range(5):
        print(AudioSTT().stt('C:\\Users\\tutu\\Downloads\\audio_from_glasses.wav'))
        # print(server.stt('C:\\Users\\tutu\\Downloads\\你是谁.m4a'))

if __name__ == "__main__":
    main()

# # model = whisper.load_model("medium")
# # model = whisper.load_model("small")
# model = whisper.load_model("base")
#
# # load audio and pad/trim it to fit 30 seconds
# print('当前文件夹: ', os.getcwd())
# audio = whisper.load_audio("output.mp3")
# audio = whisper.pad_or_trim(audio)
#
# # make log-Mel spectrogram and move to the same device as the model
# mel = whisper.log_mel_spectrogram(audio).to(model.device)
#
# # detect the spoken language
# _, probs = model.detect_language(mel)
# print(f"Detected language: {max(probs, key=probs.get)}")
#
# # decode the audio
# options = whisper.DecodingOptions()
# result = whisper.decode(model, mel, options)
#
# # print the recognized text
# print(result.text)