#!/usr/bin/python
# -*- coding: utf-8 -*-

import takahe

def protogenesis_msc(sentences, output_sent_num = 50):

    """
    原生多语句压缩
    :param sentences: 待压缩的输入语句集合
    :param output_sent_num: 输出语句的个数，默认50句
    :return: 分数#句子
    """

    # 构建词图，并执行压缩
    # 忽略词数小于8的句子
    compresser = takahe.word_graph(sentences, nb_words=8, lang='en', punct_tag="PUNCT")

    # 获取压缩结果
    candidates = compresser.get_compression(output_sent_num)

    # 对压缩结果进行归一化
    results = []
    for score, path in candidates:
        normalized_score = score / len(path)
        results.append(str(round(normalized_score, 3)) + "#" + ' '.join([u[0] for u in path]))

    return results


def keyphrases_based_msc(sentences, output_sent_num = 50):

    """
    经过keyphrases重排序后的多语句压缩
    :param sentences:
    :param output_sent_num:
    :return:
    """

    # 构建词图，并执行压缩
    # 忽略词数小于8的句子
    compresser = takahe.word_graph(sentences, nb_words=8, lang='en', punct_tag="PUNCT")

    # 获取压缩结果
    candidates = compresser.get_compression(output_sent_num)

    # 利用keyphrases对压缩结果重新打分
    reranker = takahe.keyphrase_reranker(sentences, candidates, lang='en')
    reranked_candidates = reranker.rerank_nbest_compressions()

    results = []
    for score, path in reranked_candidates:
        results.append(str(round(score, 3)) + "#" + ' '.join([u[0] for u in path]))

    return results

# 测试函数
if __name__ == '__main__':

    sentences = [
        "The/DT wife/NN of/IN a/DT former/JJ U.S./NNP president/NN Bill/NNP Clinton/NNP Hillary/NNP Clinton/NNP visited/VBD China/NNP last/JJ Monday/NNP ./PUNCT",
        "Hillary/NNP Clinton/NNP wanted/VBD to/TO visit/VB China/NNP last/JJ month/NN but/CC postponed/VBD her/PRP$ plans/NNS till/IN Monday/NNP last/JJ week/NN ./PUNCT",
        "Hillary/NNP Clinton/NNP paid/VBD a/DT visit/NN to/TO the/DT People/NNP Republic/NNP of/IN China/NNP on/IN Monday/NNP ./PUNCT",
        "Last/JJ week/NN the/DT Secretary/NNP of/IN State/NNP Ms./NNP Clinton/NNP visited/VBD Chinese/JJ officials/NNS ./PUNCT"
    ]

    print '原生多语句压缩：'
    msc_results = protogenesis_msc(sentences, 50)

    for result in msc_results:
        print result;

    print '基于keyphrase重新打分的多语句压缩：'
    msc_results = keyphrases_based_msc(sentences, 50)

    for result in msc_results:
        print result;
