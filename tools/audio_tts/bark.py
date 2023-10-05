from transformers import AutoProcessor, BarkModel
import scipy
import time
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
def t2s(text, chinese=False):
    text_prompt = text
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
    chinese = True
    # generate audio from text
    # if not chinese:
    #     text_prompt = """
    #          Hello, my name is Suno. And, uh — and I like pizza. [laughs]
    #          [music]But I also have other interests [clears throat] such as playing tic tac toe.
    #     """
    # else:
    #     text_prompt = """
    #          你好吗，[music]我是土土，明天我们一起出去玩吧？[clears throat]
    #          好长时间没有看见你了，很想念你...对了，听说西湖边有很好的咖啡馆，一起去吧。
    #     """

    # 关于每次读取preset都要连接huggingface的问题：
    # 把models/bark或bark-small里的speaker_embeddings_path.json最开头的
    # "repo_or_path": "ylacombe/bark-small"改为"repo_or_path": "D:\models\bark-small"即可
    if not chinese:
        voice_preset = "v2/en_speaker_1"
        # voice_preset = "v2/en_speaker_6"
    else:
        voice_preset = "v2/zh_speaker_9"

    # inputs = processor(
    #     text_prompt,
    #     history_prompt = 'zh_speaker_1')
    inputs = processor(text_prompt, voice_preset=voice_preset)

    inputs.to('cuda')
    print('====================4========================')

    audio_array = model.generate(**inputs)
    print('====================5========================')
    audio_array = audio_array.cpu().numpy().squeeze()
    print('====================6========================')

    sample_rate = model.generation_config.sample_rate
    scipy.io.wavfile.write("bark_out.wav", rate=sample_rate, data=audio_array)

    print('====================7========================')
    # from bark import SAMPLE_RATE, generate_audio, preload_models
    # from scipy.io.wavfile import write as write_wav
    # preload_models()
    # history_prompt = "D:/bark/bark/assets/prompts/zh_speaker_0.npz"
    # audio_array = generate_audio(text, =history_prompt)
    # write_wav("/path/to/audio_2.wav", SAMPLE_RATE, audio_array)




    # from bark import SAMPLE_RATE, generate_audio, preload_models
    # from scipy.io.wavfile import write as write_wav
    #
    # preload_models()
    #
    # prompt = "Hello, my name is Suno. And, uh — and I like pizza. [laughs] But I also have other interests such as playing tic tac toe."
    #
    # history_prompt = "/path/to/history_prompt.npz"
    #
    # audio_array = generate_audio(prompt, history_prompt=history_prompt)
    #
    # write_wav("/path/to/audio_2.wav", SAMPLE_RATE, audio_array)

def main():
    # t2s(
    #     """
    #          Hello, my name is Mike Seaver. And, uh — and I like pizza. [laughs]
    #          But I also have other interests [clears throat] such as playing tic tac toe.
    #     """
    # )
    t2s('今天天气真不错，要不我们出去玩吧！')

if __name__ == "__main__" :
    main()
