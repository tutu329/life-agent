# 安装：pip install -U openai-whisper
# 依赖安装ffmpeg：choco install ffmpeg
# 网页：https://github.com/openai/whisper

import whisper
import os

# class audio_stt():
#     def __int__(self):
#         pass

# model = whisper.load_model("medium")
# model = whisper.load_model("small")
model = whisper.load_model("base")

# load audio and pad/trim it to fit 30 seconds
print('当前文件夹: ', os.getcwd())
audio = whisper.load_audio("output.mp3")
audio = whisper.pad_or_trim(audio)

# make log-Mel spectrogram and move to the same device as the model
mel = whisper.log_mel_spectrogram(audio).to(model.device)

# detect the spoken language
_, probs = model.detect_language(mel)
print(f"Detected language: {max(probs, key=probs.get)}")

# decode the audio
options = whisper.DecodingOptions()
result = whisper.decode(model, mel, options)

# print the recognized text
print(result.text)