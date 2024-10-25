# Semantic Systems
*Semantic systems refer to technologies and methods that enable machines to understand, interpret, and process data in a way that is meaningful to humans. These systems are built on the principles of semantics, which is the study of meaning in language.*

Hence,  I start by introducing ontoloies, that play a central role in semantic systems, as the provide a strutured framework to represent knowledge within a specific domain.


## Ontologies

Studer(98):
* Formal, explicit specification of a shared conceptualization. *



### Ontology Engineering

What can we do with ontologies? 


- Ontology Design
- Ontology Mapping (Comparison)
- Ontology Merging (Combination) 
- Ontology Learning (retrieving ontologies from a set of information resources) 
- Ontology Population



### How to create ontologies: 
According to Noy & McGuiness: 

![[def_1.png]]



What to do with Ontologies? 

### Reasoning with Ontologies
Useful for: 
- **Consistency Checking**
	- Check if Ontology is inherently consistent
- **Satisfiablity Checking**
	- Are there classes that cannot possibly have any instances ? 
- **Class Inference**
- **Instance Inferences**


### RDF
Standard Information Exchange is key, hence there is the need to introduce a standarized format $\rightarrow$ **R**esource **D**escription **F**ramework. 


A single RDF Building block consists of 
- **Subject**: a resource that may be identified with a URI
- **Predicate**: a URI-identified specification of the relationship between subject and object
- **Object**: a resource or literal to which the subject is related. 

![[images/def_2.png]]

**Structure**
- <subject> <predicate> <object>
- Every triple is seperated by a "."
- Two shortcuts for several statements about the same subject
- “;” introduce another predicate of the same subject
-  “,” introduce another object with the same predicate and subject

![Test](images/def_3.png)

- Prefixes for namespaces can be set with an '@'

![Test](images/def_4.png)





