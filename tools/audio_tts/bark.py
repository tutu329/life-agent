from transformers import AutoProcessor, BarkModel
import scipy
import time

import nltk  # we'll use this to split into sentences
import numpy as np

from bark.generation import (
    generate_text_semantic,
    preload_models,
)
from bark.api import semantic_to_waveform
from bark import generate_audio, SAMPLE_RATE

# from bark import generate_audio, SAMPLE_RATE
# from scipy.io.wavfile import write as write_wav

print('====================1========================')
# processor = AutoProcessor.from_pretrained("D:/models/bark")
processor = AutoProcessor.from_pretrained("D:/models/bark-small")
print('====================2========================')
# model = BarkModel.from_pretrained("D:/models/bark")
model = BarkModel.from_pretrained("D:/models/bark-small")
model.to('cuda')
print('====================3========================')

# 装饰器
def get_run_time(func):
    def wrapper(*args, **kwargs):
        start = time.time() # func开始的时间
        func(*args, **kwargs)
        end = time.time() # func结束的时间
        print(f"{func.__name__}()的运行时间为:{end - start:.1f}秒")
    return wrapper

@get_run_time
def t2s_long(text, chinese=False, output_file="bark_out.wav"):
    if not chinese:
        # voice_preset = "v2/en_speaker_1"
        voice_preset = "v2/en_speaker_6"
    else:
        voice_preset = "v2/zh_speaker_9"
    text = text.replace('\n', ' ').strip()

    sentences = nltk.sent_tokenize(text)

    GEN_TEMP = 0.6
    SPEAKER = "v2/en_speaker_6"
    silence = np.zeros(int(0.25 * SAMPLE_RATE))  # quarter second of silence

    pieces = []
    for sentence in sentences:
        semantic_tokens = generate_text_semantic(
            sentence,
            history_prompt=SPEAKER,
            temp=GEN_TEMP,
            min_eos_p=0.05,  # this controls how likely the generation is to end
        )

        audio_array = semantic_to_waveform(semantic_tokens, history_prompt=SPEAKER, )
        pieces += [audio_array, silence.copy()]

    # Audio(np.concatenate(pieces), rate=SAMPLE_RATE)

    sample_rate = model.generation_config.sample_rate
    scipy.io.wavfile.write(output_file, rate=sample_rate, data=np.concatenate(pieces))

@get_run_time
def t2s(text, chinese=False, output_file="bark_out.wav"):
    if not chinese:
        # voice_preset = "v2/en_speaker_1"
        voice_preset = "v2/en_speaker_6"
    else:
        voice_preset = "v2/zh_speaker_9"
    text = text.replace('\n', ' ').strip()

    # sentences = nltk.sent_tokenize(text)
    # silence = np.zeros(int(0.25 * SAMPLE_RATE))  # quarter second of silence
    #
    # pieces = []
    # for sentence in sentences:
    #     semantic_tokens = generate_text_semantic(
    #         sentence,
    #         history_prompt=SPEAKER,
    #         temp=GEN_TEMP,
    #         min_eos_p=0.05,  # this controls how likely the generation is to end
    #     )
    #
    #     audio_array = semantic_to_waveform(semantic_tokens, history_prompt=SPEAKER, )
    #     pieces += [audio_array, silence.copy()]

    # [laughter]
    # [laughs]
    # [sighs]
    # [music]
    # [gasps]
    # [clears throat]
    # — or ... for hesitations
    # ♪ for song lyrics
    # CAPITALIZATION for emphasis of a word
    # [MAN] and [WOMAN] to bias Bark toward male and female speakers, respectively

    # 关于每次读取preset都要连接huggingface的问题：
    # 把models/bark或bark-small里的speaker_embeddings_path.json最开头的
    # "repo_or_path": "ylacombe/bark-small"改为"repo_or_path": "D:\models\bark-small"即可

    inputs = processor(text, voice_preset=voice_preset)

    inputs.to('cuda')
    print('====================4.5========================')

    audio_array = model.generate(**inputs)
    print('====================5========================')
    audio_array = audio_array.cpu().numpy().squeeze()
    print('====================6========================')

    sample_rate = model.generation_config.sample_rate
    scipy.io.wavfile.write(output_file, rate=sample_rate, data=audio_array)

    print('====================7========================')


def main():
    t2s_long(
        """
             Hello, my name is Mike Seaver. And, uh — and I like pizza. [laughs]
             But I also have other interests [clears throat] such as playing tic tac toe.
        """
    )
    # t2s('今天天气真不错，要不我们出去玩吧！')

if __name__ == "__main__" :
    main()
