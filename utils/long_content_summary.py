from config import Prompt_Limitation
def long_content_summary(in_llm, in_content):
    print(f'==========long_content_summary(长度{len(in_content)}) =============')
    content = in_content
    if len(content) <= Prompt_Limitation.context_max_len:
        # 如果文本长度没有超过Prompt_Limitation.context_max_len(4096)，则直接返回
        return content

    # 如果文本长度超过Prompt_Limitation.context_max_len(4096)，进行分段精简并汇编
    import re
    # 分隔符：\n，句号，\t，前后可以跟着任意数量的额外空格
    paras = re.split(r'\s*[\n。.\t]\s*',content)
    # paras = content.split(' \n\t。')
    para_len = 0
    content_list_to_summary = []
    one_content = ''
    for para in paras:
        one_content += para + '\n'
        para_len += len(para)
        if para_len >= Prompt_Limitation.context_max_len:
            content_list_to_summary.append(one_content)
            one_content = ''
            para_len = 0

    answer_list = []
    for content in content_list_to_summary:
        print(f'==========需要总结的文本(长度{len(content)})为: =============\n{content}')
        question = f'"{content}", 请对这些文字进行总结，总结一定要简明扼要、要抓住重点、字数要少于100字，不要进行解释，直接返回总结后的文字'
        gen = in_llm.ask_prepare(question).get_answer_generator()
        print(f'--------------------------------该文本的总结结果--------------------------------\n')
        answer = ''
        for chunk in gen:
            print(chunk, end='', flush=True)
            answer += chunk
        print()
        print(f'-----------------------------------------------------------------------------\n')

        answer_list.append(answer)

    final_answer = ''
    answers = '\n'.join(answer_list)
    question = f'"{answers}", 请对这些文字进行总结，总结一定要简明扼要、要抓住重点、字数要少于2000字，不要进行解释，直接返回总结后的文字'
    print(f'==========需要总结的文本(长度{len(answers)})为: =============\n{answers}')
    if len(answers) >= Prompt_Limitation.context_max_len:
        print('异常：需要总结的文本长度超限。建议调整策略。')
        return []
    print(f'--------------------------------该文本的总结结果--------------------------------\n')
    gen = in_llm.ask_prepare(question).get_answer_generator()
    return gen
    # final_answer = ''
    # for chunk in gen:
    #     print(chunk, end='', flush=True)
    #     final_answer += chunk
    # print(f'-----------------------------------------------------------------------------\n')
    #
    # return final_answer