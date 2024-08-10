> "In the nights when I cannot sleep, thoughts crowd into my mind ...
> Whence and how do they come? I do not know and I have nothing to do with it. Those which please me, I keep in my head an hum them."



# Working definition of Information
What is information? For this question, many different concepts and theories exist. I'll try to create a helpful overview by listing various well established definitions before defining a working definition in this project.

### 1. Oxford Dictionary
According to the Oxford dictionary, Information can be defined as "*facts or details about somebody/something*", with leads to the need of defining what a "Fact" or "Detail" as well as what "something" entails.
In order to get  going, some working definitions have to be made here.

### 2. More perspectives:
Information is a classic polysemantic word, where it's semantic meaning is largely dependent the given perspective. 

Hence I want to list the, to my understanding, most common perspectives on Information:


* **Philosophical Perspective:** <br>
Strongly related with notions such as reference, meaning and representation: semantic information has
intentionality −“aboutness”−, it is directed to other things


* **Scientific Perspective**: <br>
Problems are expressed in terms of a notion of information amenable to
quantification
* **Mathematical Persepective**:
<br/><br/>
    * **Fisher Information:**<br>
      Measures the dependence of a random variable X on an unknown parameter θ upon which
the probability of X depends
  <br/><br/>
    * **Algorithmic information**:<br> 
      Measures the length of the shortest program that produces a string on a universal [Turing machine](../utils/turing_machines/notes_turing). 
  <br/><br/>
    * **von Neumann Entropy**<br>
      Gives a measure of the quantum resources necessary to faithfully encode the state of the source-system;
      <br/><br/>
    * **Shannon Entropy**:<br> is concerned with the statistical
properties of a given system and the correlations between the states of two systems,
independently of the meaning and any semantic content of those states. Nowadays, Shannon’s
theory is a basic ingredient of the communication engineers training. 



### 3. Shannon's Communication/Information Theory
According to Shannon (1948; see also Shannon and Weaver 1949), a general
communication system consists of five parts:

* A source S, which generates the message to be received at the destination.

* A transmitter T, which turns the message generated at the source into a signal to be transmitted.
In the cases in which the information is encoded, encoding is also implemented by this system.

* A channel CH, that is, the medium used to transmit the signal from the transmitter to the
receiver.
* A receiver R, which reconstructs the message from the signal.
* A destination D, which receives the message. 
<br><br>
 ![img.png](img.png)



#### Central Definitions: 
**Information as a Decrease in Uncertainty**
Information is defined as a decrease in uncertainty. For example, if Bob is trying to guess which shape Alice is holding, and Alice tells him it is blue, this reduces the set of possible shapes, thereby decreasing Bob's uncertainty.

**Entropy**
Entropy quantifies the amount of uncertainty involved in the value of a random variable or the outcome of a random process. It is measured by the formula

$$\[H(X) := -\sum_{x \in X} p(x) \log p(x)\]$$


where $\[H(X)]$ can be seen as a degree of suprise, or spoken very causually, might be seen as the number of yes/no question one needs to ask (and get answered) to obtain a certain message)



**Link from Physics to Informationtheory & Entropy**
To quote from [Maxwell and his deamon](https://www.ias.ac.in/public/Volumes/reso/015/06/0548-0560.pdf):

> Moral. The 2nd law of thermodynamics has the same degree of truth as the statement that if you throw a tumberflu of water into the sea, you cannot ge tthe same tumblerflu of water out again


which led to physicists speaking about micro- and macrostates where entropy became a physical equivalent of probabilty: The entropy of a given macro state is the logarithm of the number of possbiel micro-states.

More on that can be found here: [Maxwells Daemon](https://www.spektrum.de/lexikon/physik/maxwellscher-daemon/9530)

![image](https://github.com/user-attachments/assets/5599af96-48a8-4bb3-aa01-f51bac960a77)

This daemon led Szilárd to close the loop leading to shannons conception of entropy by establishing that every time, maxwells daemon had to make a (particel) decsion, it costs the daemon a certain "something", which can be defined as *Information*.

So eventually, it is all one problem. 
To reduce entropy in a box of gas, to perfom useful work, one pays the price of information.

**Binary Digits (Bits)**
Shannon introduced the concept of binary digits, or bits, as the fundamental unit of information. A bit is a binary digit that can take on one of two values, typically 0 or 1. This concept revolutionized the way information was quantified and transmitted.


 



# Ways of Information-Representation

Due to limited time in this project, I limited the forms of information-representations to sets of language symbols (or corresponding sounds) $\Rightarrow$ will be abstracted as representations of Symbols (Letters), Words and Sentences.

## Information as Language Symbols: 

 [Edward Gibson](https://bcs.mit.edu/directory/edward-gibson prosed or cited an interesting idea, namely that human language is constructed by us humans via words/sentences and serves as a tool to communicate with our fellows about things that are important to us. At least to me, this is very fascinating and led me to question wether you can identify what things are important to certain groups by comparing the relativ amount of descriptive words per topic that their languages contain? 
 
Apparently, across different language families, one can see structural patterns in word specifications per objects. For example, he claimed that in more tribal societies, the number speakable colour-categories is way smaller that in more modern (capitalistic) societies.


## What is it's minimal/essential structure of Language/Text? 
Linguistics defining the smallest meaningful constituent of a linguistic expression as **morpheme** and assumes that the meaning of a sentence consists of stacked morphemes. 
But this opens even more questions up to me: 
1) How can one identify **Morphemes**? 
2) How do single Morphemes compound to the total meaning (if something like this exists) of a whole sentence / text?  Where does the entire meaning rise from? 


### Text-Representations
In order to analyse the meaning of text(s) 
### Encoding
**Encoding** is the process of converting categorical data into numerical data. It is often used to prepare data for machine learning algorithms that require numerical input

**Assumption**: Every letter, and hence every text  can be encoded as a number (Example: ASCII).
<br>With Standard ASCII, every Letter corresponds to **7 Bit**. Trough removal of redundancy, for example via the [Shannon-Fano compression](../utils/shannon_fano_coding.py), this number can be reduced slightly further, but nonetheless still more or less stupidly (or at least free of awareness of semantics) stores every letter explicitly
and defines Information as a concatenation of symbols (letters).

### Embedding
**Embedding** refers to the process of transforming data into a dense vector representation that captures semantic relationships. Common forms of emeddings include: 

* **1-Word-1Vector**:
  * Word2Vec (Skip-Gram & CBOW)
  * Glove
  * A lot of specialized variants of the two
* **1-Word-1-Vector+Char-n-grams**  
  * FastText(based on Word2Vec)
* **Contextualized / context dependent / complex structure (char or word piece based)** 
  *   ELMo
  * Transformers a la [BERT](../Embeddings/Bert.md) and its variants





## Measuring Information?
### Kolmogorov Complexity

Kolmogorov complexity is a concept in algorithmic information theory that quantifies the complexity of a string based on the length of the shortest program (or description) that can produce that string when executed on a universal Turing machine. It provides a formal way to measure the information content or randomness of individual strings, distinguishing between simple and complex data.

### Definition

The Kolmogorov complexity $$ K(x) $$ of a string $x$ is defined as:

$$
K(x) := \min_p \{ \ell(p) : U(p) = x \}
$$

where $U$ is a universal Turing machine, $p$ is a program that outputs $x$, and $\ell(p)$ is the length of the program in bits. This means that $K(x)$ is the length of the shortest effective description of $x$ .

### Intuition and Examples

Intuitively, a string is considered simple if it can be described concisely, such as "the string of one million zeros." Conversely, a string is complex if it lacks a shorter description, like a random sequence of digits. For example:

- The string "00000000" can be described as "zero repeated 8 times," making its Kolmogorov complexity low.
- A random string of 8 bits, such as "10101100," has a high Kolmogorov complexity because it cannot be compressed into a shorter description without losing information .

### Incompressibility

A string is termed **incompressible** if its Kolmogorov complexity is at least as long as the string itself, that is:

$$K(x) \geq |x|
$$

This implies that there is no shorter program that can generate the string, indicating a high level of randomness or complexity .

### Applications

Kolmogorov complexity has significant implications in various fields, including:

- **Information Theory**: It helps in understanding the limits of data compression and the nature of information.
- **Machine Learning**: It can be used to evaluate the complexity of models and data sets.
- **Philosophy**: It raises questions about the nature of randomness and the definition of information .

In summary, Kolmogorov complexity provides a rigorous framework for analyzing the complexity of strings and understanding the fundamental limits of computation and information.