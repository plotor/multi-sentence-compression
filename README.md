## multi-sentence compression

This project is the realization of multi-sentence compression. It’s a process based on the word graph, compressing multiple sentences which have the similar description and topic, and generate the sentence with the main topic and information.

[![AUR](https://img.shields.io/aur/license/yaourt.svg)](https://github.com/procyon-lotor/multi-sentence-compression/blob/master/LICENSE)

The specific algorithm thinking can refer the below two papers:

1. [Multi-sentence compression: finding shortest paths in word graphs](http://dl.acm.org/citation.cfm?id=1873818)
2. [Multiple alternative sentence compressions for automatic text summarization](http://www.umiacs.umd.edu/~dmzajic/papers/DUC2007.pdf)

These papers put forward an effective method based on word graph and word frequency, and combining K shortest path algorithm to generate summary for multiple sentences with similar topic. The process as below:

1. Adding the first sentence, taking each word as a node. Attaching a “start” node and a “end” node to initialize the word graph.
2. Adding the rest sentences to the word graph in turn:

> - If the word in the current sentence already have mapped node in the graph, namely, a word in the graph have the same word form and word class, then map the word to the node directly.
> - If the word in the current sentence has no mapped node in the graph, a new mode should be created.


![image](https://github.com/procyon-lotor/procyon-lotor.github.io/blob/master/images/2017/wordgraph.png?raw=false)

On calculating the weight of word graph edge, the method only consider the factor of word frequency. In my opinions, the method is a little single for it will bring some noise and lead to the losing of main messages.

This project take the event, namely "subject-verb-object" as the factor to calculate the weight of word graph edges. First, we use the results of events clustering and take the distance between current events and the center of clustering as the weight, then use the formula below to calculate the weight of each word in the word graph:

![image](https://github.com/procyon-lotor/procyon-lotor.github.io/blob/master/images/2017/msc_1.png?raw=false)

dis(i, e) is the cosine distance between word "i" and event "e", w(e) is the weight of event, size(E) is the size of current topic. If the corresponding word of a node appear in a sentence or several sentences many times, its weight will be accumulated.

About the calculation of edges w(i,j), we do as below formula considering the weight of "i" and "j":

![image](https://github.com/procyon-lotor/procyon-lotor.github.io/blob/master/images/2017/msc_2.png?raw=false)

pos(s,i) is the horizontal displacement of the word "i" in the sentence "s".

Divide the sum of all the edges’ weight on path by path’s length, the sentence’s path score will be got. The original compression method take the k sentence as the final output, this project introduce tri-gram language model to grade each compressing alternative sentences to reflect the sentences’ fluency.

[takahe](https://github.com/boudinfl/takahe) realize the method in the original paper, this project do the improvement on the basis of it. The usage and dependencies can refer to takahe, and thanks to the author.
