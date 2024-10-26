from openai import OpenAI
import openai

# 设置api-key和LLM的地址
oai = OpenAI(
    # http_client=openai.DefaultHttpxClient(verify=False),  # 阿里云购买了正式证书（可以是免费的）后，即可开启verify，也就是去掉本行
    # api_key='empty',
    api_key='csk-238pkvx4wx95pxedt54wnn2kwk66329jk3typ4dx4dxr3k3n',
    # base_url='https://172.27.67.106:8001/v1',
    base_url="https://api.cerebras.ai/v1",
    # base_url='https://powerai.cc:8001/v1',
    # base_url=config.Global.llm_url,
    # base_url='https://localhost:8001/v1',
    # base_url='http://127.0.0.1:8001/v1',

    # base_url='http://localhost:8001/v1',
    # api_key='sk-c1d34a4f21e3413487bb4b2806f6c4b8',
    # base_url='https://api.deepseek.com/v1',
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

    # import pprint
    # x = {"messages": [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "萧山电力公司介绍一下"}, {"role": "assistant", "content": "国网浙江杭州市萧山区供电公司为国家中型供电企业，是国网浙江省电力公司的全资子公司，以建设和运营电网为核心业务，承担着保障更安全、更经济、更清洁、可持续电力供应的基本使命。公司始建于1963年，目前下设10个职能部室、4个业务支撑机构、5个供电所(中心)。供电区域约960平方公里，总用户数57.6万户，电网规模位居全省县级供电企业首位。"}]}
    # y = {"messages": [{"role": "system", "content": "You are a helpful assistant."}, {"role": "user", "content": "萧山电网情况介绍一下"}, {"role": "assistant", "content": "萧山地区电网情况：2023年全年社会用电量226.47亿千瓦时，同比增长5.05%；售电量192.9亿千瓦时,增长4.39%。最高负荷396.4万千瓦，同比增长3.7%。2023年城市供电可靠率99.9991%，与同比上升0.0004个百分点；农村供电可靠率99.9973%，同比上升0.0021个百分点。电压合格率99.999%，与去年持平。2023全年共处理工单6012张，城市故障报修平均到达现场时间19.21分钟，农村故障报修平均到达现场时间23.98分钟，边远地区故障报修平均到达现场时间23.61分钟。"}]}
    # pprint.pprint(x)
    # pprint.pprint(y)




