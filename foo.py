from openai import OpenAI
import openai

# 设置api-key和LLM的地址
oai = OpenAI(
    # http_client=openai.DefaultHttpxClient(verify=False),  # 阿里云购买了正式证书（可以是免费的）后，即可开启verify，也就是去掉本行
    # api_key='empty',
    # base_url='https://172.27.67.106:8001/v1',
    # base_url='https://powerai.cc:8001/v1',
    # base_url=config.Global.llm_url,
    # base_url='https://localhost:8001/v1',
    # base_url='http://127.0.0.1:8001/v1',

    # base_url='http://localhost:8001/v1',
    api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
    base_url='https://api.deepseek.com/v1',
)


# 流式输出的调用
def message_stream(gen):
    for chunk in gen:
        if chunk.choices and hasattr(chunk.choices[0].delta, "content") and chunk.choices[0].delta.content is not None:
            yield chunk.choices[0].delta.content

def main():
    try:
        # 获取LLM服务器上的具体模型id
        model_id = oai.models.list().data[0].id
        print(f'模型id：{model_id!r}')

        messages = [{'role': 'system','content': 'You are a helpful assistant.'},{'role': 'user','content': '你是谁？'}]

        # 向LLM发送messages
        mid=model_id
        # mid='deepseek-chat'
        # mid='deepseek-coder'
        gen = oai.chat.completions.create(model=mid,temperature=0.7,messages=messages,stream=True,max_tokens=1024,)

        # 流式输出LLM的回复
        for chunk in message_stream(gen):
            print(chunk, end='', flush=True)

    except Exception as e:
        print(f'访问LLM服务器报错：{e}')

def call_qwen2_audio():
    from io import BytesIO
    from urllib.request import urlopen
    import librosa
    from transformers import Qwen2AudioForConditionalGeneration, AutoProcessor

    model_path = "D:\\models\\Qwen2-Audio-7B-Instruct"
    processor = AutoProcessor.from_pretrained(model_path)
    model = Qwen2AudioForConditionalGeneration.from_pretrained(model_path, device_map="auto")

    conversation = [
        {"role": "user", "content": [
            {"type": "audio",
             "audio_url": "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen2-Audio/audio/guess_age_gender.wav"},
        ]},
        {"role": "assistant", "content": "Yes, the speaker is female and in her twenties."},
        {"role": "user", "content": [
            {"type": "audio",
             "audio_url": "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen2-Audio/audio/translate_to_chinese.wav"},
        ]},
    ]
    text = processor.apply_chat_template(conversation, add_generation_prompt=True, tokenize=False)
    audios = []
    for message in conversation:
        if isinstance(message["content"], list):
            for ele in message["content"]:
                if ele["type"] == "audio":
                    audios.append(librosa.load(
                        BytesIO(urlopen(ele['audio_url']).read()),
                        sr=processor.feature_extractor.sampling_rate)[0]
                                  )

    inputs = processor(text=text, audios=audios, return_tensors="pt", padding=True)
    inputs.input_ids = inputs.input_ids.to("cuda")

    generate_ids = model.generate(**inputs, max_length=256)
    generate_ids = generate_ids[:, inputs.input_ids.size(1):]

    response = processor.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]

    print(response)

def call_funasr():
    pass

if __name__ == '__main__':
    main()
    # call_funasr()
    # call_qwen2_audio()




