
def main():
    import interpreter, openai

    # ================================================================
    # self.temperature = 0.001
    # self.api_key = None
    # self.auto_run = False
    # self.local = False
    # self.model = "gpt-4"
    # self.debug_mode = False
    # self.api_base = None          # Will set it to whatever OpenAI wants
    # self.context_window = 2000    # For local models only
    # self.max_tokens = 750         # For local models only
    # # Azure OpenAI
    # self.use_azure = False
    # self.azure_api_base = None
    # self.azure_api_version = None
    # self.azure_deployment_name = None
    # self.azure_api_type = "azure"
    # ================================================================

    # interpreter.model = "gpt-4"
    # interpreter.model = "gpt-3.5-turbo"
    # interpreter.api_key = "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"


    openai.api_key = "EMPTY"  # Not support yet
    openai.api_base = "http://127.0.0.1:8000/v1"
    # openai.Model = "Qwen-7B"

    interpreter.model = "Qwen-7B"
    interpreter.api_base = "http://127.0.0.1:8000/v1"
    # interpreter.api_base = "http://116.62.63.204:8000/v1"
    interpreter.api_key = "EMPTY"
    # interpreter.api_type = "azure"
    interpreter.use_azure = False
    # interpreter.azure_api_base = "your_azure_api_base"
    # interpreter.azure_api_version = "your_azure_api_version"
    # interpreter.azure_deployment_name = "your_azure_deployment_name"
    # interpreter.azure_api_type = "azure"

    interpreter.reset()
    interpreter.chat('what is your name?')
    # interpreter.chat('what is the content in test.xlsx?')

    # interpreter.chat("Plot AAPL and META's normalized stock prices") # Executes a single command
    # interpreter.chat() # Starts an interactive chat

def main1():
    import sys
    print(sys.executable)

def main2():
    import interpreter, openai

    openai.api_key = "EMPTY"  # Not support yet
    # openai.api_key = "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"
    openai.api_base = "http://116.62.63.204:8000/v1"
    openai.Model = "Qwen-7B"

    interpreter.auto_run = True
    interpreter.api_key = "none"
    # interpreter.api_key = "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"
    # interpreter.model = "Qwen-7B"
    # interpreter.model = "gpt-3.5-turbo"
    interpreter.temperature = 0

    def test_hello_world():
        interpreter.reset()
        messages = interpreter.chat(
            """Please reply with just the words "Hello, World!" and nothing else. Do not run code.""",
            return_messages=True)
        assert messages == [{'role': 'user',
                             'content': 'Please reply with just the words "Hello, World!" and nothing else. Do not run code.'},
                            {'role': 'assistant', 'content': 'Hello, World!'}]

    def test_math():
        interpreter.reset()
        messages = interpreter.chat(
            """Please perform the calculation 27073*7397 then reply with just the integer answer with no commas or anything, nothing else.""",
            return_messages=True)
        assert "200258981" in messages[-1]["content"]

    def test_delayed_exec():
        interpreter.reset()
        interpreter.chat(
            """Can you write a single block of code and run_code it that prints something, then delays 1 second, then prints something else? No talk just code. Thanks!""",
            return_messages=True)

    def test_nested_loops_and_multiple_newlines():
        interpreter.reset()
        interpreter.chat(
            """Can you write a nested for loop in python and shell and run them? Also put 1-3 newlines between each line in the code. Thanks!""",
            return_messages=True)

    def test_markdown():
        interpreter.reset()
        interpreter.chat(
            """Hi, can you test out a bunch of markdown features? Try writing a fenced code block, a table, headers, everything. DO NOT write the markdown inside a markdown code block, just write it raw.""")

    # test_markdown()
    interpreter.reset()
    interpreter.chat('what is the content in test.xlsx?')
    # interpreter.chat('draw a green circle.')

def main5():
    import interpreter

    interpreter.auto_run = True
    interpreter.local = True
    interpreter.debug_mode = True
    interpreter.model = "C:/Users/tutu/models/WizardCoder-Python-34B-V1.0-GPTQ"
    interpreter.temperature = 0
    interpreter.reset()
    interpreter.chat('what is the content in test.xlsx?')

if __name__ == "__main__" :
    main5()

