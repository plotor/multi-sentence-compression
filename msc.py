#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import panda

def protogenesis_msc(sentences, output_sent_num = 50):

    """
    原生多语句压缩
    :param sentences: 待压缩的输入语句集合
    :param output_sent_num: 输出语句的个数，默认50句
    :return: 分数#句子
    """

    # 构建词图，并执行压缩
    # 忽略词数小于8的句子
    compresser = panda.word_graph(sentences, nb_words=8, lang='en', punct_tag="PUNCT")

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

    if len(sys.argv) != 2:
        print 'ERROR: please specify the topic dir!'
        sys.exit(1)

    '''子句所在文件路径'''
    sentences_dir = sys.argv[1]

    for parent, dirs, files in os.walk(sentences_dir + "/weighted"):
        # 依次遍历每个主题文件
        for filename in files:
            print os.path.join(parent, filename) + ' is compressing...'
            # 加载文本
            text = open(os.path.join(parent, filename), 'r')
            # 依次处理文本
            clusted_sentences = {}  # 存放一个主题下的句子集合，按类别组织
            sentences = []
            for line in text:
                line = line.strip()
                if line.startswith('classes_'):
                    # 当前为类别分隔符
                    sentences = []
                    clusted_sentences[line] = sentences
                else:
                    sentences.append(line)

            for key in clusted_sentences:
                print key
                # 执行多语句压缩
                for sent in clusted_sentences[key]:
                    print sent

            sys.exit(1)