#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
:Name:
    panda_plus

:Authors:
    Zhenchao Wang

:Version:
    0.1

:Date:
    2015-11-19

:Description:
    panda_plus is a multi-sentence compression module. Given a set of redundant
    sentences, a word-graph is constructed by iteratively adding sentences to 
    it. The best compression is obtained by finding the shortest path in the
    word graph. The original algorithm was published and described in
    [filippova:2010:COLING]_. A keyphrase-based reranking method, described in
    [boudin-morin:2013:NAACL]_ can be applied to generate more informative 
    compressions.

    .. [filippova:2010:COLING] Katja Filippova, Multi-Sentence Compression: 
       Finding Shortest Paths in Word Graphs, *Proceedings of the 23rd 
       International Conference on Computational Linguistics (Coling 2010)*, 
       pages 322-330, 2010.
    .. [boudin-morin:2013:NAACL] Florian Boudin and Emmanuel Morin, Keyphrase 
       Extraction for N-best Reranking in Multi-Sentence Compression, 
       *Proceedings of the 2013 Conference of the North American Chapter of the
       Association for Computational Linguistics: Human Language Technologies 
       (NAACL-HLT 2013)*, 2013.


:History:
    Development history of the panda module:
        - 0.1 (2015-11-19), first version

:Dependencies:
    The following Python modules are required:
        - `networkx <http://networkx.github.com/>`_ for the graph construction
          (v1.2+)

:Usage:
    A typical usage of this module is::
    
        import panda
        
        # A list of tokenized and POS-tagged sentences
        sentences = ['Hillary/NNP Clinton/NNP wanted/VBD to/stop visit/VB ...']
        
        # Create a word graph from the set of sentences with parameters :
        # - minimal number of words in the compression : 6
        # - language of the input sentences : en (english)
        # - POS tag for punctuation marks : PUNCT
        compresser = takahe.word_graph( sentences, 
                                        nb_words = 6, 
                                        lang = 'en', 
                                        punct_tag = "PUNCT" )

        # Get the 50 best paths
        candidates = compresser.get_compression(50)

        # 1. Rerank compressions by path length (Filippova's method)
        for cummulative_score, path in candidates:

            # Normalize path score by path length
            normalized_score = cummulative_score / len(path)

            # Print normalized score and compression
            print round(normalized_score, 3), ' '.join([u[0] for u in path])

        # Write the word graph in the dot format
        compresser.write_dot('test.dot')

        # 2. Rerank compressions by keyphrases (Boudin and Morin's method)
        reranker = takahe.keyphrase_reranker( sentences,  
                                              candidates, 
                                              lang = 'en' )

        reranked_candidates = reranker.rerank_nbest_compressions()

        # Loop over the best reranked candidates
        for score, path in reranked_candidates:
            
            # Print the best reranked candidates
            print round(score, 3), ' '.join([u[0] for u in path])

:Misc:
    The Takahe is a flightless bird indigenous to New Zealand. It was thought to
    be extinct after the last four known specimens were taken in 1898. However, 
    after a carefully planned search effort the bird was rediscovered by on 
    November 20, 1948. (Wikipedia, http://en.wikipedia.org/wiki/takahe)  
"""

import sys
import codecs
import os
import re
import Queue
import networkx as nx

from common.logger import logging


class WordGraph:

    """
    The word_graph class constructs a word graph from the set of sentences given
    as input. The set of sentences is a list of strings, sentences are tokenized
    and words are POS-tagged (e.g. ``"Saturn/NNP is/VBZ the/DT sixth/JJ 
    planet/NN from/IN the/DT Sun/NNP in/IN the/DT Solar/NNP System/NNP"``). 
    Four optional parameters can be specified:

    - nb_words is is the minimal number of words for the best compression 
      (default value is 8).
    - lang is the language parameter and is used for selecting the correct 
      stopwords list (default is "en" for english, stopword lists are localized 
      in /resources/ directory).
    - punct_tag is the punctuation mark tag used during graph construction 
      (default is PUNCT).
    """

    def __init__(self, sentence_list, grammar_scorer, nb_words=8, lang="en", punct_tag="PUNCT", pos_separator='/'):

        self.sentence = list(sentence_list)
        """ A list of sentences provided by the user. """

        self.length = len(sentence_list)
        """ The number of sentences given for fusion. """
        
        self.nb_words = nb_words
        """ The minimal number of words in the compression. """

        self.resources = os.path.dirname(__file__) + '/resources/'
        """ The path of the resources folder. """

        self.stopword_path = self.resources+'stopwords.'+lang+'.dat'
        """ The path of the stopword list, e.g. stopwords.[lang].dat. """

        self.stopwords = self.load_stopwords(self.stopword_path)
        """ The set of stopwords loaded from stopwords.[lang].dat. """

        self.punct_tag = punct_tag
        """ The stopword tag used in the graph. """

        self.pos_separator = pos_separator
        """ The character (or string) used to separate a word and its Part of Speech tag """

        self.grammar_scorer = grammar_scorer
        """ language model scorer """

        self.graph = nx.DiGraph()
        """ The directed graph used for fusion. """
    
        self.start = '-start-'
        """ The start token in the graph. """

        self.stop = '-end-'
        """ The end token in the graph. """

        self.sep = '/-/'
        """ The separator used between a word and its POS in the graph. """
        
        self.term_freq = {}
        """ The frequency of a given term. """

        self.term_weight = {}
        """The weight of a given term. """
        
        self.verbs = set(['VB', 'VBD', 'VBP', 'VBZ', 'VH', 'VHD', 'VHP', 'VBZ', 'VV', 'VVD', 'VVP', 'VVZ'])
        """
        The list of verb POS tags required in the compression. At least *one* 
        verb must occur in the candidate compressions.
        """

        # Replacing default values for French
        if lang == "fr":
            self.verbs = set(['V', 'VPP', 'VINF'])

        # 1. 预处理，将句子中的word/pos/weight，按照空格切分成（word, pos, weight）
        self.pre_process_sentences()

        # 2. 统计每个词的词频，及其总权重
        self.compute_statistics()

        # 3. 构建词图
        self.build_graph()

    def pre_process_sentences(self):

        """
        预处理：将字符串形式的句子中的词格式化成（word, pos, weight）
        """

        for i in range(self.length):
        
            # 将句子中的空格统一化，然后去除每个词的首尾空格
            self.sentence[i] = re.sub(' +', ' ', self.sentence[i])
            self.sentence[i] = self.sentence[i].strip()  # 删除句子的首尾空格
            
            # 按空格切分成词word/pos/weight
            words = self.sentence[i].split(' ')

            # 创建一个空的词容器（word, pos, weight）
            container = [(self.start, self.start, 1.0)]

            # 循环处理句子中的每个词
            for w in words:
                
                # 将每个词的word, pos, weight分离
                pos_separator_re = re.escape(self.pos_separator)
                m = re.match("^(.+)" + pos_separator_re + "(.+)" + pos_separator_re + "(\d+(\.\d+)*)$", w)
                token, pos, weight = m.group(1), m.group(2), m.group(3)

                # 循环添加词
                container.append((token.lower(), pos, float(weight)))
                    
            # 添加尾结点
            container.append((self.stop, self.stop, 1.0))

            self.sentence[i] = container

    def compute_statistics(self):

        """
        计算每个词的词频和总权重
        """

        # key：词；value：包含该词的句子的序号
        terms = {}

        # key：词，value：该词在各包含该词的句子中的权重
        weights = {}

        # 遍历sentences
        for i in range(self.length):

            # 依次处理句子中的(word, pos, weight)
            for token, pos, weight in self.sentence[i]:

                # 生成word/-/pos标签
                node = token.lower() + self.sep + pos  # node = word/-/pos

                # 以word/-/pos为key，value中存储包含该词的句子的序号
                if node not in terms:
                    terms[node] = [i]
                else:
                    terms[node].append(i)

                # 以word/-/pos为key，value中存储该词在各个句子中的权重
                if node not in weights:
                    weights[node] = [weight]
                else:
                    weights[node].append(weight)

        # 遍历处理terms中的keys
        for key in terms:
            # 统计每个词的词频
            self.term_freq[key] = len(terms[key])

        # 遍历处理weights中的keys
        for key in weights:
            # 统计每个词的总权重
            tw = 0.0
            for w in weights[key]:
                tw += w
            self.term_weight[key] = tw

    def build_graph(self):

        """
        - 迭代添加句子，构建有向连通词图，词语添加顺序：

        1. 没有候选结点或者具有明确的候选结点或者在一个句子中出现多次的非停用词

        2. 具有多个候选结点的非停用词

        3. 停用词

        4. 标点

        对于2、3、4，如果具有多个候选结点，则选择上下文和词图中的邻接结点覆盖度最大的结点。

        - 为词图添加边

        词图中的每个结点是一个元组('word/POS', id)，同时附加一个info信息，info为一个列表，
        其中存储每个包含该词的句子sentence_id和在句子中的位置position_in_sentence

        """

        # 逐个添加句子
        for i in range(self.length):

            # 计算句子的长度（包含的词数）
            sentence_len = len(self.sentence[i])

            # 标记，用0初始化
            mapping = [0] * sentence_len

            # -------------------------------------------------------------------
            # 1. 没有候选结点或者具有明确的候选结点或者在一个句子中出现多次的非停用词
            # -------------------------------------------------------------------
            for j in range(sentence_len):

                token, pos, weight = self.sentence[i][j]

                # 如果是停用词或者标点，则跳过
                if token in self.stopwords or re.search('(?u)^\W$', token):
                    continue

                # 结点标识：word/-/pos
                node = token.lower() + self.sep + pos

                # 计算图中可能的候选结点的个数
                k = self.ambiguous_nodes(node)

                # 如果图中没有结点，则新建一个结点，id为0
                if k == 0:

                    # 添加一个id为0的结点，i为句子编号，j为当前词在句子中的编号
                    self.graph.add_node((node, 0), info=[(i, j)], label=token.lower())

                    # Mark the word as mapped to k
                    mapping[j] = (node, 0)

                # 只有一个匹配的结点（即id为0的结点）
                elif k == 1:

                    # 获取包含当前结点的句子ID
                    ids = []
                    for sid, pos_s in self.graph.node[(node, 0)]['info']:
                        # sid为node所在句子id, pos_s为该词在句子中的位置
                        ids.append(sid)

                    # 如果该结点之前没有记录，则更新该结点（更新info的值）
                    if i not in ids:
                        self.graph.node[(node, 0)]['info'].append((i, j))
                        mapping[j] = (node, 0)

                    # 否则为当前冗余的词创建一个新的结点
                    else:
                        self.graph.add_node((node, 1), info=[(i, j)], label=token.lower())
                        mapping[j] = (node, 1)

            # -------------------------------------------------------------------
            # 2. 具有多个候选结点的非停用词
            # -------------------------------------------------------------------
            for j in range(sentence_len):

                token, pos, weight = self.sentence[i][j]

                # 如果是停用词或者标点，则跳过
                if token in self.stopwords or re.search('(?u)^\W$', token):
                    continue

                # 处理步骤1中未处理的词
                if mapping[j] == 0:

                    # 结点标识：word/-/pos
                    node = token.lower() + self.sep + pos

                    # 创建邻接结点的标识
                    prev_token, prev_pos, prev_weight = self.sentence[i][j-1]  # 前一个词的word和pos
                    next_token, next_pos, next_weight = self.sentence[i][j+1]  # 后一个词的word和pos
                    prev_node = prev_token.lower() + self.sep + prev_pos
                    next_node = next_token.lower() + self.sep + next_pos

                    # 计算图中可能的候选结点的个数
                    k = self.ambiguous_nodes(node)

                    # 寻找候选结点中具有最大上下文覆盖度或最大频度的结点
                    ambinode_overlap = []
                    ambinode_frequency = []

                    # 依次处理每个候选结点
                    for l in range(k):

                        # 获取结点的上文
                        l_context = self.get_directed_context(node, l, 'left')

                        # 获取结点的下文
                        r_context = self.get_directed_context(node, l, 'right')

                        # 计算对应node在相应上下文中出现的总次数
                        val = l_context.count(prev_node)
                        val += r_context.count(next_node)

                        # 保存每个候选结点的上下文覆盖度
                        ambinode_overlap.append(val)

                        # 保存每个候选结点的频度
                        ambinode_frequency.append(len(self.graph.node[(node, l)]['info']))

                    # 寻找最佳候选结点（避免环路）
                    found = False
                    selected = 0
                    while not found:

                        # 覆盖度最大的结点下标
                        selected = self.max_index(ambinode_overlap)

                        # 如果覆盖度不能区分，则用最大的频度
                        if ambinode_overlap[selected] == 0:
                            selected = self.max_index(ambinode_frequency)

                        # 获取句子对应的ID
                        ids = []
                        for sid, p in self.graph.node[(node, selected)]['info']:
                            ids.append(sid)

                        # 避免环路
                        if i not in ids:
                            found = True
                            break

                        # Remove the candidate from the lists
                        else:
                            del ambinode_overlap[selected]
                            del ambinode_frequency[selected]

                        # Avoid endless loops
                        if len(ambinode_overlap) == 0:
                            break

                    # 找到不为当前句子的最佳候选结点
                    if found:
                        self.graph.node[(node, selected)]['info'].append((i, j))
                        mapping[j] = (node, selected)

                    # 否则，创建一个新的结点
                    else:
                        self.graph.add_node((node, k), info=[(i, j)], label=token.lower())
                        mapping[j] = (node, k)

            # -------------------------------------------------------------------
            # 3. 处理停用词
            # -------------------------------------------------------------------
            for j in range(sentence_len):

                token, pos, weight = self.sentence[i][j]

                # 如果不是停用词，则跳过
                if token not in self.stopwords:
                    continue

                # 结点标识：word/-/pos
                node = token.lower() + self.sep + pos

                # 获取候选结点的数目
                k = self.ambiguous_nodes(node)

                # If there is no node in the graph, create one with id = 0
                if k == 0:

                    # Add the node in the graph
                    self.graph.add_node((node, 0), info=[(i, j)], label=token.lower())

                    # Mark the word as mapped to k
                    mapping[j] = (node, 0)

                # Else find the node with overlap in context or create one
                else:

                    # Create the neighboring nodes identifiers
                    prev_token, prev_pos, prev_weight = self.sentence[i][j-1]
                    next_token, next_pos, next_weight = self.sentence[i][j+1]
                    prev_node = prev_token.lower() + self.sep + prev_pos
                    next_node = next_token.lower() + self.sep + next_pos

                    ambinode_overlap = []

                    # For each ambiguous node
                    for l in range(k):

                        # Get the immediate context words of the nodes, the
                        # boolean indicates to consider only non stopwords
                        l_context = self.get_directed_context(node, l, 'left', True)
                        r_context = self.get_directed_context(node, l, 'right', True)

                        # Compute the (directed) context sum
                        val = l_context.count(prev_node)
                        val += r_context.count(next_node)

                        # Add the count of the overlapping words
                        ambinode_overlap.append(val)

                    # Get best overlap candidate
                    selected = self.max_index(ambinode_overlap)

                    # Get the sentences id of the best candidate node
                    ids = []
                    for sid, pos_s in self.graph.node[(node, selected)]['info']:
                        ids.append(sid)

                    # Update the node in the graph if not same sentence and
                    # there is at least one overlap in context
                    if i not in ids and ambinode_overlap[selected] > 0:

                        # Update the node in the graph
                        self.graph.node[(node, selected)]['info'].append((i, j))

                        # Mark the word as mapped to k
                        mapping[j] = (node, selected)

                    # Else create a new node
                    else:
                        # Add the node in the graph
                        self.graph.add_node((node, k), info=[(i, j)], label=token.lower())

                        # Mark the word as mapped to k
                        mapping[j] = (node, k)

            # -------------------------------------------------------------------
            # 4. 处理标点
            # -------------------------------------------------------------------
            for j in range(sentence_len):

                token, pos, weight = self.sentence[i][j]

                # 如果不是标点，则跳过
                if not re.search('(?u)^\W$', token):
                    continue

                # 结点标识：word/-/pos
                node = token.lower() + self.sep + pos

                # 计算相似结点的数目
                k = self.ambiguous_nodes(node)

                # If there is no node in the graph, create one with id = 0
                if k == 0:

                    # Add the node in the graph
                    self.graph.add_node((node, 0), info=[(i, j)], label=token.lower())

                    # Mark the word as mapped to k
                    mapping[j] = (node, 0)

                # Else find the node with overlap in context or create one
                else:

                    # Create the neighboring nodes identifiers
                    prev_token, prev_pos, prev_weight = self.sentence[i][j-1]
                    next_token, next_pos, next_weight = self.sentence[i][j+1]
                    prev_node = prev_token.lower() + self.sep + prev_pos
                    next_node = next_token.lower() + self.sep + next_pos

                    ambinode_overlap = []

                    # For each ambiguous node
                    for l in range(k):

                        # Get the immediate context words of the nodes
                        l_context = self.get_directed_context(node, l, 'left')
                        r_context = self.get_directed_context(node, l, 'right')

                        # Compute the (directed) context sum
                        val = l_context.count(prev_node)
                        val += r_context.count(next_node)

                        # Add the count of the overlapping words
                        ambinode_overlap.append(val)

                    # Get best overlap candidate
                    selected = self.max_index(ambinode_overlap)

                    # Get the sentences id of the best candidate node
                    ids = []
                    for sid, pos_s in self.graph.node[(node, selected)]['info']:
                        ids.append(sid)

                    # Update the node in the graph if not same sentence and
                    # there is at least one overlap in context
                    if i not in ids and ambinode_overlap[selected] > 1:

                        # Update the node in the graph
                        self.graph.node[(node, selected)]['info'].append((i, j))

                        # Mark the word as mapped to k
                        mapping[j] = (node, selected)

                    # Else create a new node
                    else:
                        # Add the node in the graph
                        self.graph.add_node((node, k), info=[(i, j)], label=token.lower())

                        # Mark the word as mapped to k
                        mapping[j] = (node, k)

            # -------------------------------------------------------------------
            # 5. 添加边，通过为当前结点与其所有后继结点加边来解决边的稀疏性问题，确保无环
            # -------------------------------------------------------------------
            for pre in range(0, len(mapping) - 1):

                for pos in range(pre + 1, len(mapping)):

                    self.graph.add_edge(mapping[pre], mapping[pos])

                    # 判定是否有环
                    try:
                        # find_cycle在无环的情况下会抛出异常
                        nx.find_cycle(self.graph, source=mapping[pre], orientation='original')

                        # 没有异常，说明有环，移出刚刚添加的边
                        self.graph.remove_edge(mapping[pre], mapping[pos])

                    except:
                        # 无环
                        pass

        # 计算每条边对应的权值
        for node1, node2 in self.graph.edges_iter():
            self.graph.add_edge(node1, node2, weight=self.cal_edge_weight(node1, node2))

    def __all_successors(self, succseeor_collection, key, successors):

        if key not in succseeor_collection:
            return

        for node in succseeor_collection[key]:

            if node in successors:
                continue
            else:
                successors.add(node)
                self.__all_successors(succseeor_collection, node, successors)

    def ambiguous_nodes(self, node):

        """
        计算当前词在词图中的候选结点数目
        """

        k = 0
        while self.graph.has_node((node, k)):
            k += 1

        return k

    def get_directed_context(self, node, k, dir='all', non_pos=False):

        """
        Returns the directed context of a given node, i.e. a list of word/POS of
        the left or right neighboring nodes in the graph. The function takes 
        four parameters :

        - node is the word/POS tuple
        - k is the node identifier used when multiple nodes refer to the same 
          word/POS (e.g. k=0 for (the/DET, 0), k=1 for (the/DET, 1), etc.)
        - dir is the parameter that controls the directed context calculation, 
          it can be set to left, right or all (default)
        - non_pos is a boolean allowing to remove stopwords from the context 
          (default is false)
        """

        # Define the context containers
        l_context = []
        r_context = []

        # For all the sentence/position tuples
        for sid, off in self.graph.node[(node, k)]['info']:

            # word/-/pos
            prev = self.sentence[sid][off-1][0].lower() + self.sep + self.sentence[sid][off-1][1]
            next = self.sentence[sid][off+1][0].lower() + self.sep + self.sentence[sid][off+1][1]

            if non_pos:
                # 忽略停用词
                if self.sentence[sid][off-1][0] not in self.stopwords:
                    l_context.append(prev)
                if self.sentence[sid][off+1][0] not in self.stopwords:
                    r_context.append(next)
            else:
                # 考虑停用词
                l_context.append(prev)
                r_context.append(next)

        # 返回上文
        if dir == 'left':
            return l_context
        # 返回下文
        elif dir == 'right':
            return r_context
        # 返回上下文
        else:
            l_context.extend(r_context)
            return l_context

    def cal_edge_weight(self, node1, node2):

        """
        基于被连接的两个结点的权值来计算当前边的权重
        A node is a tuple of ('word/POS', unique_id).
        """

        # Get the list of (sentence_id, pos_in_sentence) for node1
        info1 = self.graph.node[node1]['info']
        
        # Get the list of (sentence_id, pos_in_sentence) for node2
        info2 = self.graph.node[node2]['info']
        
        # Get the frequency of node1 in the graph
        # freq1 = self.graph.degree(node1)
        # freq1 = len(info1)

        # 结点1的权重
        key = node1[0]
        if key in self.term_weight:
            weight1 = self.term_weight[key]
        else:
            return 0.0

        if weight1 == 0:
            return 0.0

        # Get the frequency of node2 in cluster
        # freq2 = self.graph.degree(node2)
        # freq2 = len(info2)

        # 结点2的权重
        key = node2[0]
        if key in self.term_weight:
            weight2 = self.term_weight[key]
        else:
            return 0.0

        if weight2 == 0:
            return 0.0

        # 公式中的diff函数
        diff = []

        # 依次处理每个句子
        for s in range(self.length):
        
            # Compute diff(s, i, j) which is calculated as
            # pos(s, i) - pos(s, j) if pos(s, i) < pos(s, j)
            # O otherwise
    
            # Get the positions of i and j in s, named pos(s, i) and pos(s, j)
            # As a word can appear at multiple positions in a sentence, a list
            # of positions is used
            pos_i_in_s = []
            pos_j_in_s = []
            
            # For each (sentence_id, pos_in_sentence) of node1
            for sentence_id, pos_in_sentence in info1:
                # If the sentence_id is s
                if sentence_id == s:
                    # Add the position in s
                    pos_i_in_s.append(pos_in_sentence)
            
            # For each (sentence_id, pos_in_sentence) of node2
            for sentence_id, pos_in_sentence in info2:
                # If the sentence_id is s
                if sentence_id == s:
                    # Add the position in s
                    pos_j_in_s.append(pos_in_sentence)
                    
            # Container for all the diff(s, i, j) for i and j
            all_diff_pos_i_j = []
            
            # Loop over all the i, j couples
            for x in range(len(pos_i_in_s)):
                for y in range(len(pos_j_in_s)):
                    diff_i_j = pos_i_in_s[x] - pos_j_in_s[y]
                    # Test if word i appears *BEFORE* word j in s
                    if diff_i_j < 0:
                        all_diff_pos_i_j.append(-1.0*diff_i_j)
                        
            # Add the mininum distance to diff (i.e. in case of multiple 
            # occurrencies of i or/and j in sentence s), 0 otherwise.
            if len(all_diff_pos_i_j) > 0:
                diff.append(1.0/min(all_diff_pos_i_j))
            else:
                diff.append(0.0)

        sum_diff = sum(diff)
        if sum_diff == 0:
            return 0.0

        return ((weight1 + weight2) / sum_diff) / (weight1 * weight2)

    def event_guided_multi_compress(self, lambd, max_neighbors, queue_size, sentence_count):

        """
        基于事件指导的多语句压缩
        利用图的广度优先搜索来得到路径，搜索过程中考虑如下因素：
        1.路径得分
        2.语言模型得分

        :return:
        """

        sentences = self.__pruning_bfs(lambd, max_neighbors, queue_size)

        # 计算句子的综合得分
        for i in range(len(sentences)):

            # 当前句子
            sentence = sentences[i]

            # 路径得分
            path_weight = 0.0
            # 句子：字符串形式
            str_sentence = ''

            for j in range(1, len(sentence) - 2):

                # 路径得分
                path_weight += self.graph.get_edge_data(sentence[j], sentence[j + 1])['weight']

                str_sentence += sentence[j][0].split(self.sep)[0] + ' '

            # 语言模型得分
            fluency_weight = self.grammar_scorer.cal_fluency(str_sentence) / len(re.split('\s+', str_sentence))

            # 依次计算每个句子的综合得分，并选择指定数目的句子进行封装返回
            sentences[i] = (len(sentence)/path_weight + lambd * fluency_weight, str_sentence.strip())

        # 按照得分从大到小进行排序，并选择指定的数目进行返回（可以考虑堆排序提升性能）
        sentences.sort(lambda x, y : cmp(x[0], y[0]), reverse=True)

        return sentences[0: sentence_count]

    def __pruning_bfs(self, lambd, max_neighbors, queue_size):

        """
        剪枝广度优先搜素
        :param lambd:
        :param max_neighbors:
        :param queue_size:
        :return:
        """

        # 存放搜索到的路径
        results = []

        # 起始结点
        start = (self.start + self.sep + self.start, 0)

        # 终止结点
        stop = (self.stop + self.sep + self.stop, 0)

        queue = Queue.Queue(queue_size)

        # 起始结点入栈
        queue.put([start])

        while not queue.empty():

            # 出队
            phrase = queue.get()

            # 获取当前短语的最后一个单词
            node = phrase[len(phrase) - 1]

            if stop == node:

                # 已经是最后一个结点
                if len(phrase) >= 8:
                    # 只选择长度在8个单词以上的句子
                    results.append(phrase)

                continue

            # 将当前短语转换成字符串形式
            str_phrase = ''

            for nodeflag, num in phrase:
                str_phrase += nodeflag.split(self.sep)[0] + ' '

            logging.info('results(' + str(len(results)) + ') queue(' + str(queue.qsize()) + ') -- ' + str_phrase)

            # 获取当前结点的邻接后继结点
            pos_neighbors = self.graph.neighbors(node)

            # 每个后继结点的综合得分（考虑路径得分和语言模型得分）
            neighbor_weight = {}

            # 依次处理每个后继结点
            for pos_neighbor in pos_neighbors:

                # 获取两个结点之间边的权重（越小越好）
                edge_weight = self.graph.get_edge_data(node, pos_neighbor)['weight']

                if edge_weight == 0:
                    continue

                # 计算当前结点与之前语句构成的新的语句的语言模型得分
                fluency_weight = self.grammar_scorer.cal_fluency(str_phrase + pos_neighbor[0].split(self.sep)[0])

                # 计算当前后继结点的综合得分
                neighbor_weight[pos_neighbor] = 1 / edge_weight + lambd * fluency_weight / (len(re.split('\s+', str_phrase)) + 1)

            # 将后继结点按综合得分由大到小进行排序（可以考虑改成推排序来提升性能）
            sort_neighbor_weight = sorted(neighbor_weight.iteritems(), key=lambda neighbor_weight : neighbor_weight[1], reverse=True)

            # 选择指定数目的结点如队列
            for i in range(min(max_neighbors, len(sort_neighbor_weight))):

                if queue.full():
                    break

                # 综合得分最高的max_neighbors个邻接后继结点如队列
                new_phrase = phrase + [sort_neighbor_weight[i][0]]
                queue.put(new_phrase)

        return results

    def load_stopwords(self, path):
        """
        This function loads a stopword list from the *path* file and returns a 
        set of words. Lines begining by '#' are ignored.
        """

        # Set of stopwords
        stopwords = set([])

        # For each line in the file
        for line in codecs.open(path, 'r', 'utf-8'):
            if not re.search('^#', line) and len(line.strip()) > 0:
                stopwords.add(line.strip().lower())

        # Return the set of stopwords
        return stopwords

    def write_dot(self, dotfile):
        """ Outputs the word graph in dot format in the specified file. """
        nx.write_dot(self.graph, dotfile)