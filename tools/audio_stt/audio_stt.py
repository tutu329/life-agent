# 安装：pip install -U openai-whisper
# win的包管理工具choco的安装(管理员模式打开powershell，然后运行)：Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://chocolatey.org/install.ps1'))
# 依赖安装ffmpeg(管理员模式打开powershell，可能需要开梯子）：choco install ffmpeg(ffmpeg不安装，会报错：FileNotFoundError: [WinError 2] 系统找不到指定的文件。)
# 网页：https://github.com/openai/whisper

import whisper
import os

def stt(in_mp3_filename, in_model='base'):
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
    res = stt('/tools/output.mp3', in_model='medium')
    print('语音所包含文字为：', res)

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