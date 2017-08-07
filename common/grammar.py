# -*- coding: utf8 -*-

import sys
import re
from common import *


class GrammarScorer(object):

    """
    语言模型打分器
    @author zhenchao.Wang 2016-1-3 15:35:00
    """

    def __init__(self, modelpath):

        self.modelpath = modelpath
        ''' 语法模型所在路径 '''

        self.ngram_model = self.__load_ngram_model()
        ''' N元语法模型 '''

    def cal_fluency(self, sentence):

        score = 0.0

        sent = '<s> ' + sentence + ' </s>'
        strs = re.split('\s+', sent)

        for i in range(2, len(strs)):

            w1 = strs[i - 2]
            w2 = strs[i - 1]
            w3 = strs[i]

            if (w1 not in self.ngram_model) and ('<s>' != w1) and ('</s>' != w1):
                w1 = '<unk>'

            if w2 not in self.ngram_model:
                w2 = '<unk>'

            if (w3 not in self.ngram_model) and ('<s>' != w3) and ('</s>' != w3):
                w3 = '<unk>'

            score += float(10**self.__extract_ngram_score(w1 + ' ' + w2 + ' ' + w3))

        return score

    def __extract_ngram_score(self, wordstr):

        """
        计算语法得分
        :param wordstr:
        :return:
        """

        words = re.split('\s+', wordstr)

        if len(words) == 3:

            if wordstr in self.ngram_model:
                return self.ngram_model[wordstr][0]

            elif (words[0] + ' ' + words[1]) in self.ngram_model:
                return self.ngram_model[words[0] + ' ' + words[1]][1] + self.__extract_ngram_score(words[0] + ' ' + words[1])

            else:
                return self.__extract_ngram_score(words[1] + ' ' + words[2])

        elif len(words) == 2:

            if (words[0] + ' ' + words[1]) in self.ngram_model:
                return self.ngram_model[words[0] + ' ' + words[1]][0]

            else:
                return self.ngram_model[words[0]][1] + self.__extract_ngram_score(words[1])

        else:
            return self.ngram_model[words[0]][0]

    def __load_ngram_model(self):

        """
        加载N元语法模型

        :return: map(word, (prob, backOffProb))
        """

        ngram_model = {}

        logging.info("loading ngram model...")

        with open(self.modelpath, mode = 'r') as modelfile:

            for line in modelfile:

                strs = re.split('\t', line.strip())

                if len(strs) < 2:
                    logging.warn('The elements count is less than 2, ignore line[' + line + ']')
                    continue

                prob_score = float(strs[0])
                tri_gram = strs[1]
                back_off_score = 0.0

                if len(strs) == 3:
                    back_off_score = float(strs[2])

                ngram_model[tri_gram] = (prob_score, back_off_score)

        logging.info("load ngram model finished!")

        return ngram_model


if __name__ == '__main__':

    modelpath = sys.argv[1]
    grammr_scorer = GrammarScorer(modelpath)

    sentence = raw_input('Please input a sentence:(blank string exit)')

    while not sentence.isspace():

        print 'language score:\t', grammr_scorer.cal_fluency(sentence)

        sentence = raw_input('Please input a sentence:(blank string exit)')