# ==================================关于bark的优化1(speaker_embeddings_path.json)==================================
# 关于每次读取preset都要连接huggingface的问题：
# 把models/bark或bark-small里的speaker_embeddings_path.json最开头的
# "repo_or_path": "ylacombe/bark-small"改为"repo_or_path": "D:\models\bark-small"即可
# ==================================关于bark的优化2(bert-base-multilingual-cased)==================================
# d:/models下：git clone https://huggingface.co/bert-base-multilingual-cased
# C:\Users\tutu\anaconda3\envs\bark\Lib\site-packages\bark下的generation.py里：
# tokenizer = BertTokenizer.from_pretrained("bert-base-multilingual-cased")
# 改为: tokenizer = BertTokenizer.from_pretrained("D:/models/bert-base-multilingual-cased")
# ==================================关于bark的优化3(并行计算)==================================
# 详见代码中的mp实现
# ==================================关于bark的优化4(kv cache)(2023-10-10测试：该版本没有官方版本快，官方版本时间为1/4！)==================================
# 本项目的bark文件夹下的api.py、generation.py、model.py即为bark的kv cache版本文件
# C:\Users\tutu\anaconda3\envs\bark\Lib\site-packages\bark下的api.py、generation.py、model.py替换为kv cache版本的文件

from transformers import AutoProcessor, BarkModel
from transformers import BertTokenizer
from bark.generation import SAMPLE_RATE, preload_models, codec_decode, generate_coarse, generate_fine, \
    generate_text_semantic
from bark import SAMPLE_RATE
from bark.api import semantic_to_waveform
from scipy.io.wavfile import write as write_wav
import nltk
# nltk.download('punkt')
import torch.multiprocessing as mp

import numpy as np
import time

import os, re
import copy

os.environ["CUDA_VISIBLE_DEVICES"] = "1"
os.environ["SUNO_USE_SMALL_MODELS"] = "1"

import numpy as np

# print('====================1========================')
processor = None
# processor = AutoProcessor.from_pretrained("D:/models/bark")
# processor = AutoProcessor.from_pretrained("D:/models/bark-small")
# print('====================2========================')
model = None
# model = BarkModel.from_pretrained("D:/models/bark")
# model = BarkModel.from_pretrained("D:/models/bark-small")
# model.to('cuda')
# print('====================3========================')

def get_run_time(func):
    def wrapper(*args, **kwargs):
        start = time.time() # func开始的时间
        func(*args, **kwargs)
        end = time.time() # func结束的时间
        print(f"{func.__name__}()的运行时间为:{end - start:.1f}秒")
    return wrapper

class TEXT_TO_SPEECH:
    def __init__(self):
        global processor
        global model
        processor = AutoProcessor.from_pretrained("D:/models/bark-small")
        model = BarkModel.from_pretrained("D:/models/bark-small")
        model.to('cuda')
        # preload_models(text_use_small=True)

        self.voice_name = "Voices/output.npz"
        self.SPEAKER = "v2/en_speaker_6"
        self.GEN_TEMP = 0.7

        self.is_chinese = False

    def generate_audio(self, sentence, count, return_dict):
        print(f'===============self.SPEAKER: {self.SPEAKER}================')
        semantic_tokens = generate_text_semantic(
            sentence,
            history_prompt=self.SPEAKER,
            temp=self.GEN_TEMP,
            min_eos_p=0.05,  # this controls how likely the generation is to end
            use_kv_caching=True
        )
        # audio_array = semantic_to_waveform(semantic_tokens)
        print('===============semantic_to_waveform() started================')
        audio_array = semantic_to_waveform(semantic_tokens, history_prompt=self.SPEAKER)
        return_dict[count] = audio_array
        # return_dict[count] = {
        #     'text':sentence,
        #     'audio':audio_array,
        # }
        # print(f'generate_audio(): count:{count}, sentence: {sentence}')

    def dump_queue(self, queue):
        """
        Empties all pending items in a queue and returns them in a list.
        """
        result = []

        for i in iter(queue.get, 'STOP'):
            result.append(i)
        time.sleep(.01)
        return result

    # 是否有超过10个以上中文字符
    def __has_many_chinese_char(self, in_string, in_gt_chinese_char=10):  # 超过10个中文字，就有可能因为ntlk分句不支持中文而使某一分句超过13-14秒从而出错
        chinese_char_num = 0
        total_char_num = len(in_string)
        for ch in in_string:
            if u'\u4e00' <= ch <= u'\u9fff':
                chinese_char_num += 1
        if chinese_char_num >= in_gt_chinese_char:
            return True
        else:
            return False

    # 中文字符串的分句
    def __chinese_sentence_tokenize(self, x):
        sents_temp = re.split('(,|，|。|！|\!|？|\?)', x)   # 分割到逗号，如果都太长，就先不管了，太长的结果是该分句输出语音有13秒之外的丢失
        # sents_temp = re.split('(：|:|,|，|。|！|\!|\.|？|\?)', x)
        sentences = []
        not_enough_char_num = 50
        not_enough_char = False
        not_appended_sentence = ''
        for i in range(len(sents_temp) // 2):
            # 分组后是：['我们是谁', '？', '你们', '。', '他们', '。', '']
            # 因此，需要2个组成一句
            sent = sents_temp[2 * i] + sents_temp[2 * i + 1]
            if 2*i+3<len(sents_temp):
                if len(not_appended_sentence + sent + sents_temp[2 * i+2] + sents_temp[2 * i + 3])<= not_enough_char_num:
                    # 前后两句加起来不足50char
                    not_appended_sentence += sent
                    not_enough_char = True
                else:
                    not_enough_char = False
            else:
                not_enough_char = False
            if not_enough_char:
                # 当前分句和后面的一个分句加起来不足50，因此等到下一个分句再考虑是否append
                pass
            else:
                sentences.append(not_appended_sentence+sent)
                not_appended_sentence = ''
        return sentences

    # 所有字符串的分句
    def __sentence_tokenize_all(self, in_string):
        if self.__has_many_chinese_char(in_string):
            sentences = self.__chinese_sentence_tokenize(in_string)
            print(f'===输入为中文，字数为{len(in_string)}===')
            self.is_chinese = True
            self.SPEAKER = "v2/zh_speaker_5"
        else:
            sentences = nltk.sent_tokenize(in_string)
            print(f'===输入非中文，字数为{len(in_string)}===')
            self.is_chinese = False
            self.SPEAKER = "v2/en_speaker_6"
        return sentences

    # @get_run_time     # 注意：这个@get_run_time加在yield函数上，就会导致yield返回None
    def all_text_to_wavs(self, text_prompt, max_sentence_num=4, wav_path="speech"):
        text_prompt = text_prompt.replace("\n", " ").strip()
        sentences = self.__sentence_tokenize_all(text_prompt)   # 根据中文或非中文分别进行分句

        groups = []

        # 将很长的sentences，分批为多个group，每个group后续生成一个wav_path_{group_index}.wav
        sentence_num_in_one_group = 0
        one_group = []
        # print('========1=========')
        for sentence in sentences:
            # print('========2=========')
            one_group.append(sentence)
            sentence_num_in_one_group += 1
            if sentence_num_in_one_group>max_sentence_num:
                groups.append(copy.deepcopy(one_group))
                # 清空one_group及计数
                one_group = []
                sentence_num_in_one_group = 0
        # 最后几个sentence不能忘记单独加入group
        groups.append(copy.deepcopy(one_group))

        # 输出多个group对应的多个wav
        group_num = 0
        # print('========3=========')
        for sentences_in_one_group in groups:
            if sentences_in_one_group==[]:
                continue

            # print('========4=========')
            print(f'======第{group_num+1}组sentence：{sentences_in_one_group}')
            output_file_name = f'{wav_path}_{group_num+1}.wav'
            self.__max_sentences_to_one_speech(sentences_in_one_group, output_file_name)
            yield output_file_name
            group_num += 1


    def __max_sentences_to_one_speech(self, sentences, wav_path="speech.wav"):
        # silence = np.zeros(int(0.25 * SAMPLE_RATE))
        count = 0

        processes = []
        queue = mp.Queue()

        token_counter = 0
        chunks = ['']
        manager = mp.Manager()
        return_dict = manager.dict()

        for sentence in sentences:
            current_tokens = len(nltk.Text(sentence))

            if token_counter + current_tokens <= 250 and self.is_chinese==False:
                # 添加在当前chunk
                token_counter += current_tokens
                chunks[-1] = chunks[-1] + "" + sentence
            else:
                if chunks==['']:
                    chunks = [sentence]
                else:
                    # 新增一个chunk
                    chunks.append('...'+sentence)   # — or ... for hesitations
                    token_counter = current_tokens

        for prompt in chunks:
            count += 1
            print(f'======count: {count}, prompt: {prompt}======')
            p = mp.Process(target=self.generate_audio, args=(prompt, count, return_dict))
            processes.append(p)
            p.start()

        queue.put('STOP')

        for process in processes:
            process.join()

        # silence = np.zeros(int(0.25 * SAMPLE_RATE))

        # voice = list(return_dict.values())
        voice = []
        for i in range(len(return_dict)):
            voice.append(return_dict[i+1])
            # voice.append(silence)  # 添加静音的停顿

            # print(f'return_dict count:{i+1}, text:{return_dict[ii+1]["text"]}')

        # save audio
        filepath = wav_path  # change this to your desired output path
        # filepath = "uploads/speech.wav"  # change this to your desired output path
        write_wav(filepath, SAMPLE_RATE, np.concatenate(voice))
    def backup__max_sentences_to_speech(self, text_prompt, wav_path="speech.wav"):
        text_prompt = text_prompt.replace("\n", " ").strip()

        sentences = self.__sentence_tokenize_all(text_prompt)   # 根据中文或非中文分别进行分句
        print(sentences)
        # sentences = nltk.sent_tokenize(text_prompt)
        silence = np.zeros(int(0.25 * SAMPLE_RATE))
        count = 0

        processes = []
        queue = mp.Queue()

        token_counter = 0
        chunks = ['']
        manager = mp.Manager()
        return_dict = manager.dict()

        for sentence in sentences:
            current_tokens = len(nltk.Text(sentence))

            if token_counter + current_tokens <= 250 and self.is_chinese==False:
                # 添加在当前chunk
                token_counter += current_tokens
                chunks[-1] = chunks[-1] + "" + sentence
            else:
                if chunks==['']:
                    chunks = [sentence]
                else:
                    # 新增一个chunk
                    chunks.append('...'+sentence)   # — or ... for hesitations
                    token_counter = current_tokens

        for prompt in chunks:
            count += 1
            print(f'======count: {count}, prompt: {prompt}======')
            p = mp.Process(target=self.generate_audio, args=(prompt, count, return_dict))
            processes.append(p)
            p.start()

        queue.put('STOP')

        for process in processes:
            process.join()

        # silence = np.zeros(int(0.25 * SAMPLE_RATE))

        # voice = list(return_dict.values())
        voice = []
        for i in range(len(return_dict)):
            voice.append(return_dict[i+1])
            # voice.append(silence)  # 添加静音的停顿

            # print(f'return_dict count:{i+1}, text:{return_dict[ii+1]["text"]}')

        # save audio
        filepath = wav_path  # change this to your desired output path
        # filepath = "uploads/speech.wav"  # change this to your desired output path
        write_wav(filepath, SAMPLE_RATE, np.concatenate(voice))

def main():
    obj = TEXT_TO_SPEECH()
    mp.set_start_method("spawn")
    # start_time = time.time()
    text0 = "what is your name?"
    text1 = "Methamphetamine is a powerful and addictive stimulant drug that affects the central nervous system. It is made by chemically altering the amphetamine molecule, which is found in some over-the-counter medications. The most common form of methamphetamine is a white crystalline powder that can be smoked, snorted, or injected. It has been associated with a range of negative health effects, including addiction, psychosis, and cardiovascular disease."
    text2 = """
    Hey, have you heard about this new text-to-audio model called "Bark"? 
    Apparently, it's the most realistic and natural-sounding text-to-audio model 
    out there right now. People are saying it sounds just like a real person speaking. 
    
    I think it uses advanced machine learning algorithms to analyze and understand the 
    nuances of human speech, and then replicates those nuances in its own speech output. 
    
    It's pretty impressive, and I bet it could be used for things like audiobooks or podcasts. 
    In fact, I heard that some publishers are already starting to use Bark to create audiobooks. 
    It would be like having your own personal voiceover artist. 
    
    I really think Bark is going to be a game-changer in the world of text-to-audio technology.
    """
    obj.__max_sentences_to_speech(text0)
    # end_time = time.time()

    # print(f"Time taken to generate audio with {len(text)} words is {end_time - start_time} seconds.")

if __name__ == "__main__":
    main()

