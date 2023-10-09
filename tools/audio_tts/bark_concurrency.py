from transformers import AutoProcessor, BarkModel
from transformers import BertTokenizer
from bark.generation import SAMPLE_RATE, preload_models, codec_decode, generate_coarse, generate_fine, \
    generate_text_semantic
from bark import SAMPLE_RATE
from bark.api import semantic_to_waveform
from scipy.io.wavfile import write as write_wav
import nltk
import torch.multiprocessing as mp

import numpy as np
import time

import os

os.environ["CUDA_VISIBLE_DEVICES"] = "0"
os.environ["SUNO_USE_SMALL_MODELS"] = "1"

import numpy as np

print('====================1========================')
# processor = AutoProcessor.from_pretrained("D:/models/bark")
processor = AutoProcessor.from_pretrained("D:/models/bark-small")
print('====================2========================')
# model = BarkModel.from_pretrained("D:/models/bark")
model = BarkModel.from_pretrained("D:/models/bark-small")
model.to('cuda')
print('====================3========================')

def get_run_time(func):
    def wrapper(*args, **kwargs):
        start = time.time() # func开始的时间
        func(*args, **kwargs)
        end = time.time() # func结束的时间
        print(f"{func.__name__}()的运行时间为:{end - start:.1f}秒")
    return wrapper

class TEXT_TO_SPEECH:
    def __init__(self):
        preload_models(text_use_small=True)

        self.voice_name = "Voices/output.npz"
        self.SPEAKER = "v2/en_speaker_6"
        self.GEN_TEMP = 0.7

    def generate_audio(self, sentence, count, return_dict):
        semantic_tokens = generate_text_semantic(
            sentence,
            history_prompt=self.SPEAKER,
            temp=self.GEN_TEMP,
            min_eos_p=0.05,  # this controls how likely the generation is to end
            use_kv_caching=True
        )
        audio_array = semantic_to_waveform(semantic_tokens, history_prompt=self.SPEAKER)
        return_dict[count] = audio_array

    def dump_queue(self, queue):
        """
        Empties all pending items in a queue and returns them in a list.
        """
        result = []

        for i in iter(queue.get, 'STOP'):
            result.append(i)
        time.sleep(.01)
        return result

    @get_run_time
    def text_to_speech(self, text_prompt):
        # Enter your prompt and speaker here
        # if __name__ != "__main__":
        text_prompt = text_prompt.replace("\n", " ").strip()

        sentences = nltk.sent_tokenize(text_prompt)
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

            if token_counter + current_tokens <= 250:
                token_counter += current_tokens
                chunks[-1] = chunks[-1] + "" + sentence
            else:
                chunks.append(sentence)
                token_counter = current_tokens

        for prompt in chunks:
            count += 1
            p = mp.Process(target=self.generate_audio, args=(prompt, count, return_dict))
            processes.append(p)
            p.start()

        queue.put('STOP')

        for process in processes:
            process.join()

        voice = list(return_dict.values())

        # save audio
        filepath = "speech.wav"  # change this to your desired output path
        # filepath = "uploads/speech.wav"  # change this to your desired output path
        write_wav(filepath, SAMPLE_RATE, np.concatenate(voice))

def main():
    obj = TEXT_TO_SPEECH()
    mp.set_start_method("spawn")
    # start_time = time.time()
    text = "Methamphetamine is a powerful and addictive stimulant drug that affects the central nervous system. It is made by chemically altering the amphetamine molecule, which is found in some over-the-counter medications. The most common form of methamphetamine is a white crystalline powder that can be smoked, snorted, or injected. It has been associated with a range of negative health effects, including addiction, psychosis, and cardiovascular disease."
    obj.text_to_speech(text.replace("\n", " ").strip())
    # end_time = time.time()

    # print(f"Time taken to generate audio with {len(text)} words is {end_time - start_time} seconds.")

if __name__ == "__main__":
    main()

