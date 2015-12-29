#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import logging
import takahe
import panda

# 设置日志格式
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
    datefmt='%a, %d %b %Y %H:%M:%S',
    filename='../../../logs/msc.log',
    filemode='w')


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
    tmp = []
    for score, path in candidates:
        tmp.append((score / len(path), path))

    # 按照得分排序
    tmp = sorted(tmp, key = lambda tmp : tmp[0])

    # 封装结果返回
    results = []
    for score, path in tmp:
        results.append(str(round(score, 6)) + "#" + ' '.join([u[0] for u in path]) + '\n')

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
        results.append(str(round(score, 6)) + "#" + ' '.join([u[0] for u in path]) + '\n')

    return results


def event_based_msc(sentences, output_sent_num = 50):

    """
    事件驱动的多语句压缩
    :param sentences: 待压缩的输入语句集合
    :param output_sent_num: 输出语句的个数，默认50句
    :return: 分数#句子
    """

    # 构建词图，并执行压缩
    # 忽略词数小于8的句子
    compresser = panda.word_graph(sentences, nb_words=8, lang='en', punct_tag="PUNCT")

    # 获取压缩结果
    candidates = compresser.get_compression(output_sent_num)

    compresser.write_dot('graph.dot')

    # 对压缩结果进行归一化，并按得分由小到大排序
    tmp = []
    for score, path in candidates:
        tmp.append((score / len(path), path))

    # 依据得分进行排序
    tmp = sorted(tmp, key = lambda tmp : tmp[0])

    # 封装结果返回
    results = []
    for score, path in tmp:
        results.append(str(round(score, 6)) + "#" + ' '.join([u[0] for u in path]) + '\n')

    return results


def event_keyphrase_based_msc(sentences, output_sent_num=50):

    """
    基于事件来构建词图，基于keyphrase来对输出语句进行reranking
    :param sentences: 待压缩的语句
    :param output_sent_num: 输出语句的个数
    :return:得分#句子
    """

    # 构建词图，并执行压缩
    # 忽略词数小于8的句子
    compresser = panda.word_graph(sentences, nb_words=8, lang='en', punct_tag="PUNCT")

    # 获取压缩结果
    candidates = compresser.get_compression(output_sent_num)

    # 利用keyphrases对压缩结果重新打分
    reranker = takahe.keyphrase_reranker(sentences, candidates, lang='en')
    reranked_candidates = reranker.rerank_nbest_compressions()

    results = []
    for score, path in reranked_candidates:
        results.append(str(round(score, 6)) + "#" + ' '.join([u[0] for u in path]) + '\n')

    return results

# 测试函数
if __name__ == '__main__':

    if len(sys.argv) != 4:
        logging.error('Parameter error!')
        sys.exit(1)

    '''子句所在文件路径'''
    sentences_dir = sys.argv[1]

    '''输出文件路径'''
    save_dir = sys.argv[2]

    '''运行模式：1→原生&kp; 2→event; 4→event_kp; 7→all'''
    run_mode = int(sys.argv[3])

    if run_mode == 7 or run_mode == 5 or run_mode == 3 or run_mode == 1:
        '''原生多语句压缩和基于keyphrases重排序的多语句压缩'''

        for parent, dirs, files in os.walk(sentences_dir + "/tagged"):

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

                # 存放原生压缩结果
                protogenesis_results = {}

                # 存放基于关键短语重排序的结果
                keyphrased_based_resuts = {}

                for key in clusted_sentences:

                    # 执行多语句压缩
                    logging.info('[protogenesis]compressing, filename=%s, class=%s', filename, key)
                    protogenesis_results[key] = protogenesis_msc(clusted_sentences[key], 50)
                    logging.info('[protogenesis]compress success, filename=%s, class=%s', filename, key)

                    logging.info('[keyphrases]compressing, filename=%s, class=%s', filename, key)
                    keyphrased_based_resuts[key] = keyphrases_based_msc(clusted_sentences[key], 50)
                    logging.info('[keyphrases]compress success, filename=%s, class=%s', filename, key)

                logging.info('Compress file[%s] finished!', filename)

                # 保存结果到文件
                # 原生压缩结果
                savepath = save_dir + '/protogenesis'
                if not os.path.exists(savepath):
                    os.makedirs(savepath)

                logging.info('Saving file[%s]', os.path.join(savepath, filename))
                with open(os.path.join(savepath, filename), 'w') as save_file:

                    for key in protogenesis_results:
                        save_file.write(key + '\n')
                        save_file.writelines(protogenesis_results[key])
                        save_file.flush()

                logging.info('Save file[%s] success!', os.path.join(savepath, filename))

                # 基于keyphrases的压缩结果
                savepath = save_dir + '/keyphrases'
                if not os.path.exists(savepath):
                    os.makedirs(savepath)

                logging.info('Saving file[%s]', os.path.join(savepath, filename))
                with open(os.path.join(savepath, filename), 'w') as save_file:
                    for key in keyphrased_based_resuts:
                        save_file.write(key + '\n')
                        save_file.writelines(keyphrased_based_resuts[key])
                        save_file.flush()

                logging.info('Save file[%s] success!', os.path.join(savepath, filename))

    if run_mode == 7 or run_mode == 3 or run_mode == 6 or run_mode == 2:
        '''事件指导的多语句压缩'''
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
                    event_based_results[key] = event_based_msc(clusted_sentences[key], 50)
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

    # 有点问题
    if run_mode == 7 or run_mode == 6 or run_mode == 5 or run_mode == 4:
        '''事件指导的多语句压缩，并利用keyphrase对结果进行reranking'''
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
                    logging.info('[events+keyphrases]compressing, filename=%s, class=%s', filename, key)
                    event_based_results[key] = event_keyphrase_based_msc(clusted_sentences[key], 50)
                    logging.info('[events+keyphrases]compress success, filename=%s, class=%s', filename, key)

                logging.info('Compress file[%s] finished!', filename)

                # 保存结果到文件
                # 基于事件驱动的压缩结果
                savepath = save_dir + '/events_keyphrases'
                if not os.path.exists(savepath):
                    os.makedirs(savepath)

                logging.info('Saving file[%s]', os.path.join(savepath, filename))
                with open(os.path.join(savepath, filename), 'w') as save_file:
                    for key in event_based_results:
                        save_file.write(key + '\n')
                        save_file.writelines(event_based_results[key])
                        save_file.flush()

                logging.info('Save file[%s] success!', os.path.join(savepath, filename))