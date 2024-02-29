from config import Prompt_Limitation, Global
from utils.task import Flicker_Task
import re

def _split_long_content_to_paras(in_content):
    content = in_content

    # 如果文本长度超过Prompt_Limitation.context_max_len(4096)，进行分段精简并汇编
    # 分隔符：\n，句号，\t，前后可以跟着任意数量的额外空格
    # paras = re.split(r'\s*[\n。.\t]\s*',content)
    sentences = re.split(r'(?<=[.!?。？！])', content)  # 用正向后行断言，才能保留用于分割的标点。
    # paras = content.split(' \n\t。')
    para_len = 0
    paras_to_summary = []
    one_para = ''
    paras_to_append = 1

    for sentence in sentences:
        one_para += sentence + '\n'
        para_len += len(sentence)
        if para_len >= Prompt_Limitation.concurrent_para_max_len:
            if paras_to_append < Prompt_Limitation.concurrent_max_paras:
                paras_to_summary.append(one_para)
                one_para = ''
                para_len = 0
                paras_to_append += 1
            else:
                # 超过Prompt_Limitation.context_max_paragraphs的段落直接放弃
                break
    # 长度没有超限时，内容也要append
    if len(one_para) > 0:
        paras_to_summary.append(one_para)

    return paras_to_summary

def long_content_qa_concurrently(in_llm, in_content, in_prompt):
    # print(f'[long_content_summary()]: 文本长度为 {len(in_content)})')
    if len(in_content)==0:
        print('[long_content_summary()]: 异常: 输入文本长度为0')
        assert(0)
    content = in_content
    if len(content) > Prompt_Limitation.concurrent_para_max_len:
        paras_to_summary = _split_long_content_to_paras(content)

        gen = multi_contents_qa_concurrently(
            in_contents=paras_to_summary,
            in_prompt=in_prompt,
            in_content_short_enough=True,   # 如果short_enough, 则每个qa只需要调用short_content_qa而不用调用long_content_qa(分段)
        ).get_answer_generator()
    else:
        question = f'"{content}", 请严格依据这些文字，回答问题"{in_prompt}"，回答一定要调理清晰，不要解释，直接采用markdown回复。'
        gen = in_llm.ask_prepare(question).get_answer_generator()

    return gen

# 通过llm对多个内容in_contents进行并发解读，返回最终答复对应的llm对象
def multi_contents_qa_concurrently(
        in_contents,
        in_prompt,
        in_content_short_enough=False,       # 如果short_enough, 则每个qa只需要调用short_content_qa而不用调用long_content_qa(分段)
        in_api_url='http://127.0.0.1:8001/v1',
        in_search_urls=None
):
    from tools.llm.api_client import Concurrent_LLMs, LLM_Client

    llms = Concurrent_LLMs(in_url=in_api_url)
    num = len(in_contents)
    llms.init(
        in_prompts=[in_prompt]*num,
        in_contents=in_contents,
        in_content_short_enough=in_content_short_enough,
        # in_stream_buf_callbacks=None,
    )
    status = llms.start_and_get_status()
    results = llms.wait_all(status)
    summaries = results['llms_full_responses']
    i = 0
    answers = ''

    for summary in summaries:
        if in_search_urls:
            answers += f'小结[{i}]: ' + summary + '\n' + f'小结[{i}]的来源: ' + in_search_urls[i] + '\n'
        else:
            answers += f'分段[{i}]: \n' + summary + '\n'
        result_string = summary.replace('\n', '')[:50]

        i += 1
        print(f"result[{i}]: '{result_string}...'")

    print(f'answers: \n{answers}')
    llm = LLM_Client(
        url=in_api_url,
        temperature=0,
        print_input=False,
        history=False,
    )

    if in_search_urls is not None:
        final_question = f'"{answers}", 请综合考虑上述小结内容及其来源可信度，回答问题"{in_prompt}"，回答一定要简明扼要、层次清晰，如果回答内容较多，请采用markdown对其进行格式化输出。'
    else:
        final_question = f'"{answers}", 请综合考虑上述分段内容，回答问题"{in_prompt}"，回答是简略还是详细，一定要严格根据问题的要求来。'

    llm = llm.ask_prepare(
        in_question=final_question,
    )
    return llm
def multi_contents_qa_concurrently_yield(
        in_contents,
        in_prompt,
        in_content_short_enough=False,       # 如果short_enough, 则每个qa只需要调用short_content_qa而不用调用long_content_qa(分段)
        in_api_url='http://127.0.0.1:8001/v1',
        in_max_new_tokens=2048,
        in_search_urls=None,
):
    from tools.llm.api_client import Concurrent_LLMs, LLM_Client

    x=0
    print('---------------multi_contents_qa_concurrently_yield()---------------')
    for content in in_contents:
        x += 1
        print(f'content[{x}]内容: "{content[:50]}..."')
        print(f'content[{x}]长度: {len(content)}')
        print(f'prompt内容: "{in_prompt[:50]}..."')
    print('--------------------------------------------------------------------')


    llms = Concurrent_LLMs(in_url=in_api_url)
    num = len(in_contents)
    llms.init(
        in_max_new_tokens=in_max_new_tokens,
        in_prompts=[in_prompt]*num,
        in_contents=in_contents,
        in_content_short_enough=in_content_short_enough,
        # in_stream_buf_callbacks=None,
    )
    status = llms.start_and_get_status()
    results = llms.wait_all(status)
    summaries = results['llms_full_responses']
    i = 0
    answers = ''

    # line = f'{80 * "-"}\n\n'
    yield Global.line
    for summary in summaries:
        if in_search_urls:
            answers += f'小结[{i+1}]: ' + summary + '\n\n' + f'小结[{i+1}]的来源: ' + in_search_urls[i] + '\n\n' + Global.line
        else:
            answers += f'小结[{i+1}]: \n\n' + summary + '\n\n' + Global.line
        result_string = summary.replace('\n', '')[:50]

        yield f"搜索结果[{i+1}]: '{result_string}...'\n\n"
        i += 1

    yield Global.line
    llm = LLM_Client(
        url=in_api_url,
        temperature=0,
        max_new_tokens=in_max_new_tokens,
        print_input=False,
        history=False,
    )

    final_question = f'"{answers}", 请综合考虑上述小结内容及其来源可信度，回答问题"{in_prompt}"，回答一定要简明扼要、层次清晰，如果回答内容较多，请采用markdown对其进行格式化输出。'

    llm = llm.ask_prepare(
        in_question=final_question,
    )
    for chunk in llm.get_answer_generator():
        yield chunk


def long_content_qa(in_llm, in_content, in_prompt):
    # print(f'[long_content_summary()]: 文本长度为 {len(in_content)})')
    if len(in_content) == 0:
        print('[long_content_summary()]: 异常: 输入文本长度为0')
        assert (0)
    content = in_content

    print('-------------------------long_content_qa()--------------------------')
    print(f'content内容: "{content[:50]}..."')
    print(f'content长度: {len(in_content)}')
    print(f'prompt内容: "{in_prompt[:50]}..."')
    # print(f'Prompt_Limitation.context_max_len: {Prompt_Limitation.context_max_len}')
    # print(f'Prompt_Limitation.summary_max_len: {Prompt_Limitation.summary_max_len}')
    # print(f'Prompt_Limitation.context_max_paragraphs: {Prompt_Limitation.context_max_paragraphs}')
    print('--------------------------------------------------------------------')

    # 如果文本长度 > context_max_len
    if len(content) > Prompt_Limitation.concurrent_para_max_len:
        paras_to_summary = _split_long_content_to_paras(content)

        # 对每一段进行ask，并将多段的answer进行拼接
        answer_list = []
        if Prompt_Limitation.concurrent_max_paras > 1:
            for content in paras_to_summary:
                # print(f'[long_content_summary()]: 需要总结的文本(长度{len(content)})为: "{content[:50]}"')
                question = f'"{content}", 请严格依据这些文字，回答问题"{in_prompt}"，答复是简明还是详细，一定要严格按照问题要求来，字数不能大于{Prompt_Limitation.concurrent_summary_max_len}字，不要解释，直接回复'
                gen = in_llm.ask_prepare(question).get_answer_generator()
                answer = ''
                for chunk in gen:
                    # print(chunk, end='', flush=True)
                    answer += chunk
                # print()
                # print(f'[long_content_summary()]: 对文本的总结结果为 "{answer[:50]}"')

                answer_list.append(answer)
        elif Prompt_Limitation.concurrent_max_paras == 1:
            # 仅从长文本中摘取合并了一段文字(长度约为Prompt_Limitation.context_max_len)
            if paras_to_summary:
                answer_list.append(paras_to_summary[0])
            else:
                # 某一些情况下，页面content超过4000字，但分段汇总后不足4000字，会出现“content_list_to_summary.append(one_content)”没用执行到的情况，需要直接把content加进去
                answer_list.append(content)

        # final_answer = ''
        answers = '\n'.join(answer_list)
    else:
        # 如果文本长度 <= context_max_len
        answers = content

    # 对分段解读并汇编后的内容answers进行最终解读
    question = f'"{answers}", 请严格依据这些文字，回答问题"{in_prompt}"，答复是简明还是详细，一定要严格按照问题要求来，字数不能大于{Prompt_Limitation.concurrent_summary_max_len}字，不要解释，直接回复'
    # question = f'"{answers}", 请根据这些文字，回答问题"{in_prompt}"，回答一定要简明扼要，同时给出这样回答的主要依据。'
    answers_to_print = answers.replace('\n', '')[:50]
    # print(f'[long_content_summary()]: "{answers_to_print}...", 请根据这些文字，并结合问题"{in_prompt}"对文字进行总结，总结要简明扼要、逻辑合理、重点突出、一定不能有写了一半的句子，尽可能用markdown格式把总结的文字以层次清晰的方式展现出来，字数要少于1000字，不要进行解释，直接返回总结后的文字。')
    if Prompt_Limitation.concurrent_para_max_len <= 1000:
        ratio = 8.0
    elif Prompt_Limitation.concurrent_para_max_len <= 2000:
        ratio = 4.0
    elif Prompt_Limitation.concurrent_para_max_len <= 4000:
        ratio = 2.0
    elif Prompt_Limitation.concurrent_para_max_len <= 6000:
        ratio = 1.5

    # 如果汇编后的内容answers的长度超过context_max_len * ratio, 则print一个警告，并返回空内容
    if len(answers) >= Prompt_Limitation.concurrent_para_max_len * ratio:
        total = Prompt_Limitation.concurrent_para_max_len * ratio
        print(
            f'[long_content_summary()]: warning：需要总结的文本长度超过Prompt_Limitation.context_max_len({Prompt_Limitation.concurrent_para_max_len})的{ratio}倍({total})。建议调整策略。')
        # assert(0)
        return []
    # print(f'[long_content_summary()]: 该文本的总结结果为, \n')

    # 返回对answers进行解读的gen
    gen = in_llm.ask_prepare(question).get_answer_generator()
    return gen
    # final_answer = ''
    # for chunk in gen:
    #     print(chunk, end='', flush=True)
    #     final_answer += chunk
    # print(f'-----------------------------------------------------------------------------\n')
    #
    # return final_answer

def short_content_qa(in_llm, in_content, in_prompt):
    content = ''.join(in_content.split('\n'))[:40]
    print(f'----------short_content_qa(): content内容(长度{len(in_content)}): "{content}..."----------', end='')
    print(f'prompt内容: "{in_prompt[:50]}..."')
    question = f'"{in_content}", 请严格依据这些文字，回答问题"{in_prompt}"，答复是简明还是详细，一定要严格按照问题要求来，字数不能大于{Prompt_Limitation.concurrent_summary_max_len}字，不要解释，直接回复'
    gen = in_llm.ask_prepare(question).get_answer_generator()
    return gen
