from config import Prompt_Limitation
def long_content_summary(in_llm, in_content, in_prompt):
    print(f'==========long_content_summary(长度{len(in_content)}) =============')
    if len(in_content)==0:
        print('********************异常: 输入文本长度为0********************')
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
                print(f'==========需要总结的文本(长度{len(content)})为: =============\n{content}')
                question = f'"{content}", 请根据这些文字，并结合问题"{in_prompt}"对文字进行总结，总结一定要简明扼要、要抓住重点、字数要少于100字，不要进行解释，直接返回总结后的文字'
                gen = in_llm.ask_prepare(question).get_answer_generator()
                print(f'--------------------------------该文本的总结结果--------------------------------\n')
                answer = ''
                for chunk in gen:
                    print(chunk, end='', flush=True)
                    answer += chunk
                print()
                print(f'-----------------------------------------------------------------------------\n')

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


    question = f'"{answers}", 请根据这些文字，并结合问题"{in_prompt}"对文字进行总结，总结要简明扼要、逻辑合理、重点突出、一定不能有写了一半的句子，尽可能用markdown格式把总结的文字以层次清晰的方式展现出来，字数要少于1000字，不要进行解释，直接返回总结后的文字。'
    print(f'==========需要总结的文本(长度{len(answers)})为: =============\n{answers}')
    if Prompt_Limitation.context_max_len<=1000:
        ratio = 3.0
    elif Prompt_Limitation.context_max_len<=2000:
        ratio = 2.0
    elif Prompt_Limitation.context_max_len<=4000:
        ratio = 1.5
    elif Prompt_Limitation.context_max_len<=6000:
        ratio = 1.2
        
    if len(answers) >= Prompt_Limitation.context_max_len*ratio:
        print(f'************************************** warning：需要总结的文本长度超过Prompt_Limitation.context_max_len({Prompt_Limitation.context_max_len})的{ratio}倍({Prompt_Limitation.context_max_len*{ratio}})。建议调整策略。**************************************')
        # assert(0)
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