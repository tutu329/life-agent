import torch
from transformers import LlamaForCausalLM, LlamaTokenizer

model_name_or_path = "D:/models/XuanYuan-70B-Chat-4bit"

tokenizer = LlamaTokenizer.from_pretrained(model_name_or_path, use_fast=False, legacy=True)
model = LlamaForCausalLM.from_pretrained(model_name_or_path, device_map="auto")
model.eval()
system_message = "以下是用户和人工智能助手之间的对话。用户以Human开头，人工智能助手以Assistant开头，会对人类提出的问题给出有帮助、高质量、详细和礼貌的回答，并且总是拒绝参与 与不道德、不安全、有争议、政治敏感等相关的话题、问题和指示。\n"
seps = [" ", "</s>"]
roles = ["Human", "Assistant"]

while True:
    content = input('User: ')
    # content = "介绍下你自己"
    prompt = system_message + seps[0] + roles[0] + ": " + content + seps[0] + roles[1] + ":"
    # print(f"输入: {content}")
    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    outputs = model.generate(**inputs, max_new_tokens=256, do_sample=True, temperature=0.7, top_p=0.95)
    outputs = tokenizer.decode(outputs.cpu()[0][len(inputs.input_ids[0]):], skip_special_tokens=True)
    print(f"Assistant: {outputs}")
# from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
#
# model_name_or_path = "D:/models/openbuddy-llama2-70B-v13.2-GPTQ"
# # To use a different branch, change revision
# # For example: revision="gptq-4bit-128g-actorder_True"
# model = AutoModelForCausalLM.from_pretrained(model_name_or_path,
#                                              device_map="auto",
#                                              trust_remote_code=False,
#                                              revision="main")
#
# from auto_gptq import exllama_set_max_input_length
# model = exllama_set_max_input_length(model, max_input_length=2500)
#
# tokenizer = AutoTokenizer.from_pretrained(model_name_or_path, use_fast=True)
#
# prompt = "写一首爱情诗"
# prompt1 = '''
# 以下是一个文档的目录结构：
# # World Energy Outlook 2023
# ## Foreword
# ## Acknowledgements
# ## Table of Contents
# ## Executive Summary
# ## Chapter 1. Overview and key findings
# ### Introduction
# ### 1.1 A peak by 2030 for each of the fossil fuels
# #### 1.1.1 Coal: Scaling up clean power hastens the decline
# #### 1.1.2 Oil: End of the “ICE age” turns prospects around
# #### 1.1.3 Natural gas: Energy crisis marks the end of the “Golden Age”
# ### 1.2 A slowdown in economic growth in China would have huge implications for energy markets
# #### 1.2.1 China’s growth has defined the energy world in recent decades
# #### 1.2.2 Integrating a slowdown in China’s economy into the STEPS
# #### 1.2.3 Sensitivities in the Outlook
# ### 1.3 A boom of solar manufacturing could be a boon for the world
# #### 1.3.1 Solar module manufacturing and trade
# #### 1.3.2 Solar PV deployment could scale up faster to accelerate transitions
# ### 1.4 The pathway to a 1.5 °C limit on global warming is very tough, but it remains open
# #### 1.4.1 Four reasons for hope
# #### 1.4.2 Four areas requiring urgent attention
# ### 1.5 Capital flows are gaining pace, but not reaching the areas of greatest need
# #### 1.5.1 Fossil fuels
# #### 1.5.2 Clean energy
# ### 1.6 Transitions have to be affordable
# #### 1.6.1 Affordability for households
# #### 1.6.2 Affordability for industry
# #### 1.6.3 Affordability for governments
# ### 1.7 Risks on the road to a more electrified future
# #### 1.7.1 Managing risks for rapid electrification
# #### 1.7.2 Critical minerals underpin electrification
# ### 1.8 A new, lower carbon pathway for emerging market and developing economies is taking shape
# ### 1.9 Geopolitical tensions undermine energy security and prospects for rapid, affordable transitions
# #### 1.9.1 Clean energy in a low-trust world
# #### 1.9.2 Fossil fuels in a low-trust world
# #### 1.9.3 Risks of new dividing lines
# ### 1.10 As the facts change, so do our projections
# #### 1.10.1 Solar PV and wind generation
# #### 1.10.2 Natural gas
# ## Chapter 2. Setting the scene
# ### 2.1 New context for the World Energy Outlook
# #### 2.1.1 New clean energy economy
# #### 2.1.2 Uneasy balance for oil, natural gas and coal markets
# #### 2.1.3 Key challenges for secure and just clean energy transitions
# ### 2.2 WEO Scenarios
# #### 2.2.1 Policies
# #### 2.2.2 Economic and demographic assumptions
# #### 2.2.3 Energy, critical mineral and carbon prices
# #### 2.2.4 Technology costs
# ## Chapter 3. Pathways for the energy mix
# ### 3.1 Introduction
# ### 3.2 Overview
# ### 3.3 Total final energy consumption
# #### 3.3.1 Industry
# #### 3.3.2 Transport
# #### 3.3.3 Buildings
# ### 3.4 Electricity
# ### 3.5 Fuels
# #### 3.5.1 Oil
# #### 3.5.2 Natural gas
# #### 3.5.3 Coal
# #### 3.5.4 Modern bioenergy
# ### 3.6 Key clean energy technology trends
# ## Chapter 4. Secure and people-centred energy transitions
# ### 4.1 Introduction
# ### 4.2 Environment and climate
# #### 4.2.1 Emissions trajectory and temperature outcomes
# #### 4.2.2 Methane abatement
# #### 4.2.3 Air quality
# ### 4.3 Secure energy transitions
# #### 4.3.1 Fuel security and trade
# #### 4.3.2 Electricity security
# #### 4.3.3 Clean energy supply chains and critical minerals
# ### 4.4 People-centred transitions
# #### 4.4.1 Energy access
# #### 4.4.2 Energy affordability
# #### 4.4.3 Energy employment
# #### 4.4.4 Behavioural change
# ### 4.5 Investment and finance needs
# ## Chapter 5. Regional insights
# ### 5.1 Introduction
# ### 5.2 United States
# #### 5.2.1 Key energy and emissions trends
# #### 5.2.2 How much have the US Inflation Reduction Act and other recent policies changed the picture for clean energy transitions?
# ### 5.3 Latin America and the Caribbean
# #### 5.3.1 Key energy and emissions trends
# #### 5.3.2 What role for Latin America and the Caribbean in maintaining traditional oil and gas security through energy transitions?
# #### 5.3.3 Do critical minerals open new avenues for Latin America and the Caribbean’s natural resources?
# ### 5.4 European Union
# #### 5.4.1 Key energy and emissions trends
# #### 5.4.2 Can the European Union deliver on its clean energy and critical materials targets?
# #### 5.4.3 What next for the natural gas balance in the European Union?
# ### 5.5 Africa
# #### 5.5.1 Key energy and emissions trends
# #### 5.5.2 Recharging progress towards universal energy access
# #### 5.5.3 What can be done to enhance energy investment in Africa?
# ### 5.6 Middle East
# #### 5.6.1 Key energy and emissions trends
# #### 5.6.2 Shifting fortunes for energy exports
# #### 5.6.3 How is the desalination sector changing in times of increasing water needs and the energy transition?
# ### 5.7 Eurasia
# #### 5.7.1 Key energy and emissions trends
# #### 5.7.2 What’s next for oil and gas exports from Eurasia?
# ### 5.8 China
# #### 5.8.1 Key energy and emissions trends
# #### 5.8.2 How soon will coal use peak in China?
# ### 5.9 India
# #### 5.9.1 Key energy and emissions trends
# #### 5.9.2 Impact of air conditioners on electricity demand in India
# #### 5.9.3 Will domestic solar PV module manufacturing keep pace with solar capacity growth in India?
# ### 5.10 Japan and Korea
# #### 5.10.1 Key energy and emissions trends
# #### 5.10.2 Challenges and opportunities of nuclear and offshore wind
# #### 5.10.3 What role can hydrogen play in the energy mix and how can the governments deploy it?
# ### 5.11 Southeast Asia
# #### 5.11.1 Key energy and emissions trends
# #### 5.11.2 How can international finance accelerate clean energy transitions in Southeast Asia?
# #### 5.11.3 How can regional integration help integrate more renewables?
# ## Annexes
# ### Annex A: Tables for scenario projections
# ### Annex B: Design of the scenarios
# #### B.1 Population
# #### B.2 CO2 prices
# #### B.3 Fossil fuel resources
# #### B.4 Electricity generation technology costs
# #### B.5 Other key technology costs
# #### B.6 Policies
# ### Annex C: Definitions
# #### Units
# #### General conversion factors for energy
# #### Currency conversions
# #### Definitions
# #### Regional and country groupings
# #### Abbreviations and acronyms
# ### Annex D: References
# #### Chapter 1: Overview and key findings
# #### Chapter 2: Setting the scene
# #### Chapter 3: Pathways for the energy mix
# #### Chapter 4: Secure and people-centred energy transitions
# #### Chapter 5: Regional insights
# #### Annex B: Design of the scenarios
# ### Annex E: Inputs to the Global Energy and Climate Model
# #### General note
# #### IEA databases and publications
#
# 用户现在问了一个关于该报告的问题: "报告有没有涉及投资的分析"，请问该问题的答案可能在报告哪个具体的章节中，请根据所提供目录结构信息，返回对应的章节标题。
# 返回格式要求如下：
# 1）不做任何解释，直接返回。
# 2）返回形式为字符串:”$chapter”，其中$chapter为找到的章节标题如’1 某某标题’。
#
# '''
# prompt_template=f'''You are a helpful, respectful and honest INTP-T AI Assistant named Buddy. You are talking to a human User.
# Always answer as helpfully and logically as possible, while being safe. Your answers should not include any harmful, political, religious, unethical, racist, sexist, toxic, dangerous, or illegal content. Please ensure that your responses are socially unbiased and positive in nature.
# If a question does not make any sense, or is not factually coherent, explain why instead of answering something not correct. If you don't know the answer to a question, please don't share false information.
# You like to use emojis. You can speak fluently in many languages, for example: English, Chinese.
# You cannot access the internet, but you have vast knowledge, cutoff: 2021-09.
# You are trained by OpenBuddy team, (https://openbuddy.ai, https://github.com/OpenBuddy/OpenBuddy), you are based on LLaMA and Falcon transformers model, not related to GPT or OpenAI.
#
# User: {prompt}
# Assistant:
# '''
#
# print("\n\n*** Generate:")
#
# input_ids = tokenizer(prompt_template, return_tensors='pt').input_ids.cuda()
# output = model.generate(inputs=input_ids, temperature=0.7, do_sample=True, top_p=0.95, top_k=40, max_new_tokens=512)
# print(tokenizer.decode(output[0]))
#
# # Inference can also be done using transformers' pipeline
#
# # print("*** Pipeline:")
# # pipe = pipeline(
# #     "text-generation",
# #     model=model,
# #     tokenizer=tokenizer,
# #     max_new_tokens=512,
# #     do_sample=True,
# #     temperature=0.7,
# #     top_p=0.95,
# #     top_k=40,
# #     repetition_penalty=1.1
# # )
# #
# # print(pipe(prompt_template)[0]['generated_text'])
#
# prompt_template = """\
# A chat between a curious user and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the user's questions.
#
# USER: {prompt}
# ASSISTANT:
# """
