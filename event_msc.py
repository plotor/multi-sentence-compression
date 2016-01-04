# -*- coding: utf8 -*-


"""
基于事件指导的多语句压缩
"""

import os

from common import *
import panda.panda_plus as pp


def event_based_msc(sentences, output_sent_num = 50):

    """
    事件驱动的多语句压缩
    :param sentences: 待压缩的输入语句集合
    :param output_sent_num: 输出语句的个数，默认50句
    :return: 分数#句子
    """

    # 构建词图，并执行压缩
    # 忽略词数小于8的句子
    compresser = pp.WordGraph(sentences, ngram_modelpath=r'E:\nlp\Language Model\giga_3gram.lm', nb_words=8, lang='en', punct_tag="PUNCT")

    # 获取压缩结果
    candidates = compresser.multi_compress(output_sent_num)

    # 将图保存成文本形式
    # compresser.write_dot('graph.dot')

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


if __name__ == '__main__':

    '''子句所在文件路径'''
    sentences_dir = r'E:\nlp\experiment\event-guided-mts\sub-sentences'

    '''输出文件路径'''
    save_dir = r'E:\nlp\experiment\event-guided-mts\msc_results'

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