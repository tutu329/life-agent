# 注1：vllm要增加：--enable-auto-tool-choice --tool-call-parser hermes
# "--enable-auto-tool-choice --tool-call-parser hermes" 主要用于openai-agents的tool调用，其中qwq-32b需要--tool-call-parser hermes

# 注2：推理deepseek的vllm可能要增加(https://github.com/vllm-project/vllm/pull/17784)：
# --enable-auto-tool-choice --tool-call-parser deepseek_v3 --chat-template examples/tool_chat_template_deepseekv3.jinja

# pip install openai-agents

import asyncio
from openai import AsyncOpenAI

from pydantic import BaseModel

from agents import Agent, Runner, function_tool, set_default_openai_client, set_default_openai_api, set_tracing_disabled, OpenAIChatCompletionsModel

url = "http://powerai.cc:28002/v1"
api_key = "empty"
model_name = 'qwq-32b'
client = AsyncOpenAI(
    base_url=url,
    api_key=api_key,
)
set_default_openai_client(client=client, use_for_tracing=False)
set_default_openai_api("chat_completions")
set_tracing_disabled(disabled=True)


class Weather(BaseModel):
    city: str
    temperature_range: str
    conditions: str


@function_tool
def get_weather(city: str) -> Weather:
    print("[debug] get_weather called")
    return Weather(city=city, temperature_range="14-20C", conditions="Sunny with wind.")


agent = Agent(
    model=OpenAIChatCompletionsModel(model=model_name, openai_client=client),
    name="Hello world",
    instructions="You are a helpful agent.",
    tools=[get_weather],
)


async def main():
    result = await Runner.run(agent, input="What's the weather in Tokyo?")
    print(result.final_output)
    # The weather in Tokyo is sunny.


if __name__ == "__main__":
    asyncio.run(main())
