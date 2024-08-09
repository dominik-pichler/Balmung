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

# Thoughts
## Information 
- [What is it ?](notes/what_is_information.md) 
- [What is it made of ?](notes/what_is_information.md)
- [How can it be found (and turned into knowledge?)](notes/quest_for_knowledge.md)
- [How can it be used optimally to answer questions?](https://github.com/dominik-pichler/Balmung?tab=readme-ov-file#4-ask-me-anything---qa-system)
- [What can't be known? - Is there unatainable Information ?](notes/the_unknown.md)
  
This is a repo tries to gradually find more sophisticated answers to those questions, either through code or rambling style posts.
Feel free to contact me if you're interested



## Chaos
This section tries to focus on two fundamental questions: 
- [What happens when we lack information?](notes/Chaos.md)
- [How should we deal, when faced with chaotic lack of information?](notes/Chaos.md)
____
# Tools

 ## 1. Do you know? - Kants Knowledge Graph
**Question:** <br>How can I visualise ideas and how can I determine connections between different ideas?  
For this approach I tried to turn philosophical ideas into knowledge graphs.

Thereby two different approaches have been used to identify entities and relationships.
1. Using [Rule based Parsing Systems](https://www.geeksforgeeks.org/rule-based-approach-in-nlp/)
2. Using an [LLM (Llama3)](https://ollama.com/) to extract entities and relationships via prompting
3. Using [BERT](Embeddings/ER_BERT.py) to extract entities and relationships directly

Eventually, the results have been visualised using `pyvis`. As the input size increased, this approach of simply 
visualising all entities and their relationships became unfeasible.
Hence, this project is on hold until I've solved the question of "*What is the most essential information?*".

## 2. Ishmaels Guide to (Topic) Fishing
**Question:** <br> How can I understand what (sub)topics are central in a given (research) area? 
<br>
Fishing for understanding in a personally new field of understanding can easily become an orientation-less wandering through a dark forest of (pseudo) knowledge. 
One might need a navigation system find the central intellectual building blocks of this new field of interest.
The aim of this project is, to build exactly this navigation system by developing a tool that automatically identifies central ideas and topics in a given field.


## 3.  Rank me if you can - Neural (Re-) Rankers
**Question:** <br> How can i find the most relevant documents for a given endeavour, in a large pool of documents? 
<br>

For this quest, I have manually implemented, trained and evaluated the performance of two prominent neural re-ranking algorithms ([K-NRM](https://arxiv.org/pdf/1706.06613) and [TK](https://www.researchgate.net/publication/339065967_Interpretable_Time-Budget-Constrained_Contextualization_for_Re-Ranking) )

Code and results can be found here: 
[TBD](TBD)

## 4. Ask me anything - QA System
**Question**: <br> How can I extend 3. with arbitrary OOV queries? 
<br>
Code and results can be found here: 
[TBD](TBD)


## 5. Compress me  - (Neural) Data-Compressors
During the projects listed above, I worked with lossless compression-algorithms to reduce data sizes (and to identify symbolic Morphemes) and thereby implemented the following algorithms: 
* [Shannon -  Fano encoding](https://github.com/dominik-pichler/Balmung/blob/main/utils/shannon_fano_coding.py)
   * Turned out as a pretty good start by losslessly compressing Kants *Critique of pure reason* by 55%
 
* Neural Compressors:
   * TBD




