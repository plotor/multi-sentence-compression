# -*- coding: utf8 -*-


"""
基于事件指导的多语句压缩
"""

import os
import sys

from common import *
from language_model.grammar import GrammarScorer
from panda.panda_plus import WordGraph


def event_based_msc(sentences, grammar_scorer, lambd, max_neighbors, queue_size, output_sent_num = 50):

    """
    事件驱动的多语句压缩
    :param sentences: 待压缩的输入语句集合
    :param output_sent_num: 输出语句的个数，默认50句
    :return: 分数#句子
    """

    # 构建词图，并执行压缩
    # 忽略词数小于8的句子
    compresser = WordGraph(sentences, grammar_scorer)

    # 获取压缩结果
    candidates = compresser.event_guided_multi_compress(lambd, max_neighbors, queue_size, output_sent_num)

    # 将图保存成文本形式
    # compresser.write_dot('graph.dot')

    # 封装结果返回
    results = []
    for score, sentence in candidates:
        results.append(str(round(score, 6)) + "#" + sentence + '\n')

    return results

if __name__ == '__main__':

    if len(sys.argv) != 7:
        print '参数错误'
        sys.exit(-1)

    '''子句所在文件路径'''
    sentences_dir = sys.argv[1]

    '''输出文件路径'''
    save_dir = sys.argv[2]

    ''' 语言模型所在路径 '''
    ngram_modelpath = sys.argv[3]

    ''' 路径得分和语言模型得分参数lambd '''
    lambd = float(sys.argv[4])

    ''' 最大后继邻接结点选择数 '''
    max_neighbors = int(sys.argv[5])

    ''' 队列容量 '''
    queue_size = int(sys.argv[6])

    # 初始化语言模型打分器
    grammar_scorer = GrammarScorer(ngram_modelpath)

    # 事件指导的多语句压缩
    for parent, dirs, files in os.walk(sentences_dir + "/weighted"):

        # 依次遍历每个主题文件
        for filename in files:

            logging.info('Compressing: %s', os.path.join(parent, filename))

            # 依次处理文本
            clusted_sentences = {}  # 存放一个主题下的句子集合，按类别组织
            sentences = []

            # 加载文本
            with open(os.path.join(parent, filename), 'r') as text:
                for line in text:
                    line = line.strip()
                    if line.startswith('classes_'):
                        # 当前为类别分隔符
                        sentences = []
                        clusted_sentences[line] = sentences
                    else:
                        sentences.append(line)

            # 存放基于事件指导的压缩结果
            event_based_results = {}

            for key in clusted_sentences:
                # 执行多语句压缩
                logging.info('[events]compressing, filename=%s, class=%s', filename, key)
                event_based_results[key] = event_based_msc(clusted_sentences[key], grammar_scorer, lambd, max_neighbors, queue_size)
                logging.info('[events]compress success, filename=%s, class=%s', filename, key)

            logging.info('Compress file[%s] finished!', filename)

            # 保存结果到文件
            # 基于事件驱动的压缩结果
            savepath = save_dir + '/events'
            if not os.path.exists(savepath):
                os.makedirs(savepath)

            logging.info('Saving file[%s]', os.path.join(savepath, filename))
            with open(os.path.join(savepath, filename), 'w') as save_file:
                for key in event_based_results:
                    save_file.write(key + '\n')
                    save_file.writelines(event_based_results[key])
                    save_file.flush()

            logging.info('Save file[%s] success!', os.path.join(savepath, filename))

    logging.info('program finish!')