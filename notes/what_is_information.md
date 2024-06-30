
# Working definition of Information
What is information? For this question, many different concepts and theories exist. I'll try to create a helpful overview by listing various well established definitions before defining a working definition in this project.

### 1. Oxford Dictionary
According to the Oxford dictionary, Information can be defined as "*facts or details about somebody/something*", with leads to the need of defining what a "Fact" or "Detail" as well as what "something" entails.
In order to get  going, some working definitions have to be made here.

* **Facts**<br>
Objectively, physically perceivable, constitutions of the senseable surroundings that let humans for theories about the 
characteristics of there surroundings (in order to give them orientation and guide their actions), that have not (yet) been falsified.

* **Approx. in Scientific Context**:<br>
Theory that has been design by following well established scientific principles and not falsified, despite being theoretically falsifiable.

* **Something** <br>
Objectively physically perceivable entity to which facts can be attributed to.

### 2. Different perspectives:
Information is a classic polysemantic word, where it's semantic meaning is largely dependent the given perspective. 
Hence I want to list the, to my understanding, most common perspectives on Information:
* **Philosophical Perspective:** <bf>
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
      Measures the length of the shortest program that produces a string on a universal [Turing machine](../turing_machines/notes_turing). 
  <br/><br/>
    * **von Neumann Entropy**<br>
      Gives a measure of the quantum resources necessary to faithfully encode the state of the source-system;
      <br/><br/>
    * **Shannon Entropy**:<br> is concerned with the statistical
properties of a given system and the correlations between the states of two systems,
independently of the meaning and any semantic content of those states. Nowadays, Shannon’s
theory is a basic ingredient of the communication engineers training. 



### 3. Shannon's Communication Theory
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



# Representation of Information
## How can Information be represented? 
Many different forms, in this project, I limit the forms of information representations to:
- Sound, encoded as Symbols $\Rightarrow$ 
- Images

Those two different representin our case, via bits and bytes, as they form the fundament of modern computers. 

## What is it's minimal structure? 
* [Shannon-Fano compression](../utils/shannon_fano_coding.py)


