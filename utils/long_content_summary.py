from config import Prompt_Limitation
def long_content_qa(in_llm, in_content, in_prompt):
    # print(f'[long_content_summary()]: 文本长度为 {len(in_content)})')
    if len(in_content)==0:
        print('[long_content_summary()]: 异常: 输入文本长度为0')
        assert(0)
    content = in_content
    if len(content) > Prompt_Limitation.context_max_len:
        # 如果文本长度超过Prompt_Limitation.context_max_len(4096)，进行分段精简并汇编
        import re
        # 分隔符：\n，句号，\t，前后可以跟着任意数量的额外空格
        # paras = re.split(r'\s*[\n。.\t]\s*',content)
        paras = re.split(r'(?<=[.!?。？！])', content)    # 用正向后行断言，才能保留用于分割的标点。
        # paras = content.split(' \n\t。')
        para_len = 0
        content_list_to_summary = []
        one_content = ''
        paras_to_append = 0
        for para in paras:
            one_content += para + '\n'
            para_len += len(para)
            if para_len >= Prompt_Limitation.context_max_len:
                if paras_to_append < Prompt_Limitation.context_max_paragraphs :
                    content_list_to_summary.append(one_content)
                    one_content = ''
                    para_len = 0
                    paras_to_append += 1
                else:
                    # 超过Prompt_Limitation.context_max_paragraphs的段落直接放弃
                    break

        answer_list = []
        if Prompt_Limitation.context_max_paragraphs > 1:
            for content in content_list_to_summary:
                # print(f'[long_content_summary()]: 需要总结的文本(长度{len(content)})为: "{content[:50]}"')
                question = f'"{content}", 请根据这些文字，回答问题"{in_prompt}"，答复一定要简明扼要、要抓住重点、字数要少于100字，不要进行解释，直接返回答复文字'
                gen = in_llm.ask_prepare(question).get_answer_generator()
                answer = ''
                for chunk in gen:
                    # print(chunk, end='', flush=True)
                    answer += chunk
                # print()
                # print(f'[long_content_summary()]: 对文本的总结结果为 "{answer[:50]}"')

                answer_list.append(answer)
        elif Prompt_Limitation.context_max_paragraphs == 1:
            # 仅从长文本中摘取合并了一段文字(长度约为Prompt_Limitation.context_max_len)
            if content_list_to_summary:
                answer_list.append(content_list_to_summary[0])
            else:
                # 某一些情况下，页面content超过4000字，但分段汇总后不足4000字，会出现“content_list_to_summary.append(one_content)”没用执行到的情况，需要直接把content加进去
                answer_list.append(content)

        # final_answer = ''
        answers = '\n'.join(answer_list)
    else:
        answers = content


    question = f'"{answers}", 请根据这些文字，回答问题"{in_prompt}"，回答一定要简明扼要，同时给出这样回答的主要依据。'
    answers_to_print = answers.replace('\n', '')[:50]
    # print(f'[long_content_summary()]: "{answers_to_print}...", 请根据这些文字，并结合问题"{in_prompt}"对文字进行总结，总结要简明扼要、逻辑合理、重点突出、一定不能有写了一半的句子，尽可能用markdown格式把总结的文字以层次清晰的方式展现出来，字数要少于1000字，不要进行解释，直接返回总结后的文字。')
    if Prompt_Limitation.context_max_len<=1000:
        ratio = 8.0
    elif Prompt_Limitation.context_max_len<=2000:
        ratio = 4.0
    elif Prompt_Limitation.context_max_len<=4000:
        ratio = 2.0
    elif Prompt_Limitation.context_max_len<=6000:
        ratio = 1.5
        
    if len(answers) >= Prompt_Limitation.context_max_len * ratio:
        total = Prompt_Limitation.context_max_len*ratio
        print(f'[long_content_summary()]: warning：需要总结的文本长度超过Prompt_Limitation.context_max_len({Prompt_Limitation.context_max_len})的{ratio}倍({total})。建议调整策略。')
        # assert(0)
        return []
    # print(f'[long_content_summary()]: 该文本的总结结果为, \n')
    gen = in_llm.ask_prepare(question).get_answer_generator()
    return gen
    # final_answer = ''
    # for chunk in gen:
    #     print(chunk, end='', flush=True)
    #     final_answer += chunk
    # print(f'-----------------------------------------------------------------------------\n')
    #
    # return final_answer


# 通过llm对多个内容in_contents进行并发解读，返回最终答复对应的llm对象
def long_content_qa_concurrently(in_contents, in_prompt, in_api_url='http://127.0.0.1:8001/v1', in_search_urls=None):
    from tools.llm.api_client import Concurrent_LLMs, LLM_Client
    llms = Concurrent_LLMs(in_url=in_api_url)
    num = len(in_contents)
    llms.init(
        in_prompts=[in_prompt]*num,
        in_contents=in_contents,
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
            answers += f'小结[{i}]: \n' + summary + '\n'
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

    final_question = f'"{answers}", 请综合考虑上述小结内容及其来源可信度，回答问题"{in_prompt}"，回答一定要简明扼要、层次清晰，如果回答内容较多，请采用markdown对其进行格式化输出。'

    llm = llm.ask_prepare(
        in_question=final_question,
    )
    return llm