# 1、需要调用本地tokenizer（Skywork-o1-Open-PRM-Qwen-2.5-7B）
# 2、调用Skywork-o1-Open-PRM-Qwen-2.5-7B的api
# 因此需要通过vllm开api，也需要提供模型的本地tokenizer

# 需要安装：
# git clone https://github.com/SkyworkAI/skywork-o1-prm-inference.git
# cd skywork-o1-prm-inference
# pip install -e .

import math
from openai import OpenAI
from transformers import AutoTokenizer
from model_utils.io_utils import prepare_input, derive_step_rewards_vllm

from config import dred, dgreen, dblue, dcyan, dyellow
from dataclasses import dataclass, field, asdict

@dataclass
class Step_Data:
    problem: str = None
    response: str = None

class LLM_PRM_Client:
    def __init__(self):
        self.tokenizer = None
        self.llm = None
        self.url = None
        self.api_key = None

        self.step_rewards_list = None

    def init(self, prm_model_path='/home/tutu/models/Skywork-o1-Open-PRM-Qwen-2.5-7B', url='https://powerai.cc:8002/v1', api_key='empty'):
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(prm_model_path, trust_remote_code=True)
            self.url = url
            self.api_key = api_key

            self.llm = OpenAI(
                api_key=self.api_key,
                base_url=self.url,
            )
        except Exception as e:
            dred(f'LLM_PRM_Client.init()报错: "{e}"')

    # 返回{'problem':'xxx', 'response':'xxx'}对应的step_rewards
    def get_step_rewards(self, step_data:Step_Data):
        datas = [asdict(step_data)]

        try:
            # data preprocessing
            processed_data = [prepare_input(d["problem"], d["response"], tokenizer=self.tokenizer, step_token="\n") for d in datas]
            input_ids, steps, reward_flags = zip(*processed_data)

            models = self.llm.models.list()
            model = models.data[0].id
            rewards = self.llm.embeddings.create(
                input=input_ids,
                model=model,
            )

            step_rewards = derive_step_rewards_vllm(rewards, reward_flags)
            # print("step_rewards:", step_rewards[0])
            # print("step_rewards:", step_rewards[1])
        except Exception as e:
            dred(f'LLM_PRM_Client.get_step_rewards()报错: "{e}"')
            return None

        self.step_rewards_list = step_rewards[0]
        return step_rewards[0]

    def get_min_reward(self):
        return min(self.step_rewards_list)

    def get_last_reward(self):
        return self.step_rewards_list[-1]

    def get_prod_reward(self):
        return math.prod(self.step_rewards_list)


def main():
    data = Step_Data(
        problem="Janet\u2019s ducks lay 16 eggs per day. She eats three for breakfast every morning and bakes muffins for her friends every day with four. She sells the remainder at the farmers' market daily for $2 per fresh duck egg. How much in dollars does she make every day at the farmers' market?",
        response="To determine how much money Janet makes every day at the farmers' market, we need to follow these steps:\n1. **Calculate the total number of eggs laid by the ducks per day.**\n   Janet's ducks lay 16 eggs per day.\n2. **Determine the number of eggs Janet uses each day.**\n   - She eats 3 eggs for breakfast every morning.\n   - She bakes muffins for her friends every day with 4 eggs.\n   So, the total number of eggs used per day is:\n   \\[\n   3 + 4 = 7 \\text{ eggs}\n   \\]\n3. **Calculate the number of eggs Janet sells at the farmers' market each day.**\n   Subtract the number of eggs used from the total number of eggs laid:\n   \\[\n   16 - 7 = 9 \\text{ eggs}\n   \\]\n4. **Determine how much money Janet makes from selling the eggs.**\n   She sells each egg for $2, so the total amount of money she makes is:\n   \\[\n   9 \\times 2 = 18 \\text{ dollars}\n   \\]\nTherefore, the amount of money Janet makes every day at the farmers' market is $\\boxed{18}$."
    )
    prm = LLM_PRM_Client()
    prm.init()
    step_rewards = prm.get_step_rewards(data)

    print(f'【data】')
    print(f'{asdict(data)}')
    print(f'【step_rewards】')
    print(step_rewards)

if __name__ == "__main__" :
    main()
