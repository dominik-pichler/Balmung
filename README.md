                                                ```
                                                            ,-----.
                                                           #,-. ,-.#
                                                          () a   e ()
                                                          (   (_)   )
                                                          #\_  -  _/#
                                                        ,'   `"""`    `.
                                                      ,'      \X/      `.
                                                     /         X     ____\
                                                    /          v   ,`  v  `,
                                                   /    /         ( <==+==> )
                                                   `-._/|__________\   ^   /
                                                  (\\)  |______@____\  ^  /
                                                    \\  |     ( )    \ ^ /
                                                     )  |             \^/
                                                    (   |             |v
                                                   <(^)>|             |
                                                     v  |             |
                                                        |             |
                                                        |_.--.__ .--._|
                                                          `==='  `==='
                                                
                                                ```

Inspired by Bacon's  "Scientia potentia est", repo tool aims to investigate knowledge, information and chaos.


# Information 
- [What is it ?](notes/what_is_information.md) 
- [What is it made of ?](notes/what_is_information.md)
- [How can it be found (and turned into knowledge?)](notes/quest_for_knowledge.md)
- [How can it be used optimally to answer questions?](https://github.com/dominik-pichler/Balmung?tab=readme-ov-file#4-ask-me-anything---qa-system)
- [What can't be known? - Is there unatainable Information ?](notes/the_unknown.md)
  
This is a repo tries to gradually find more sophisticated answers to those questions, either through code or rambling style posts.
Feel free to contact me if you're interested



# Chaos
- Introduction to chaos theory
____

 ## 1. Kants Knowledge Graph
**Question:** How can I visualize ideas and how can I determine connections between different ideas?  
For this approach I tried to turn philosophical ideas into knowledge graphs.

Thereby two different approaches have been used to identify entities and relationships.
1. Using [Rule based Parsing Systems](https://www.geeksforgeeks.org/rule-based-approach-in-nlp/)
2. Using an [LLM (Llama3)](https://ollama.com/) to extract entities and relationships via prompting
3. Using [BERT](Embeddings/ER_BERT.py) to extract entities and relationships directly

Eventually, the results have been visualised using `pyvis`. As the input size increased, this approach of simply 
visualising all entities and their relationships became unfeasible.
Hence, this project is on hold until I've solved the question of "*What is the most esstiential information?*".

More (theoretical) thoughts can be found in the following notebook: [Ramble 1](kants_knowledge_graph/ramble.md)


## 2. Ishmaels Guide to Fishing
Fishing for understanding in a personally new field of understanding can easily become an orientationless wandering through a dark forest of (pseudo) knowledge. 
One might need a navigation system find the central intellectual building blocks of this new field of interest.
The aim of this project is, to build exactly this navigation system by developing a tool that automatically identifes central ideas in a given field.


## 3. Neural (Re-) Rankers
Manually implemented, trained and evaluated the performance of two prominent neural re-ranking algorithms ([K-NRM](https://arxiv.org/pdf/1706.06613) and [TK](https://www.researchgate.net/publication/339065967_Interpretable_Time-Budget-Constrained_Contextualization_for_Re-Ranking) )

Code and results can be found here: 
[TBD](TBD)

## 4. Ask me anything - QA System
After implementing the neural re-rankers, I wanted to setup an actual QA System utilizing the top performing neural re-ranker.

Code and results can be found here: 
[TBD](TBD)


## 5. Compress me if you can
During the projects listed above, I worked with lossless compression-algorithms and implemented the following algorithms from scratch: 
* [Shannon -  Fano encoding](https://github.com/dominik-pichler/Balmung/blob/main/utils/shannon_fano_coding.py)
   * Turned out as a pretty good start by losslessly compressing Kants *Critique of pure reason* by 55%
 
* Neural Compressors:
   * TBD




