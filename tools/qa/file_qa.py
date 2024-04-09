from config import dred, dgreen, dblue, dcyan
from tools.llm.api_client import LLM_Client, Concurrent_LLMs
from io import StringIO

def files_qa(files, callbacks=None, suffixes=None):
    prompts = ['将文本的主要内容详细、有条理的列一下'] * len(files)
    contents = []
    for f in files:
        content = StringIO(f.getvalue().decode("utf-8")).read()
        contents.append(content)
        dred(f'content({len(content)}): {content[:100]}...')

    llms = Concurrent_LLMs()
    llms.init(prompts, contents, callbacks, in_extra_suffixes=suffixes)

    statuses = llms.start_and_get_status()
    task_status = llms.wait_all(statuses)

    for ans in task_status['llms_full_responses']:
        # 这里task_status是llms.start_and_get_status()结束后的最终状态
        dred('------------------')
        dgreen(ans)
