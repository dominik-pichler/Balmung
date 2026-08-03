from bertopic import BERTopic
from sklearn.datasets import fetch_20newsgroups
from nltk import bigrams
from nltk.probability import FreqDist
from math import log
import numpy as np

# Load a sample dataset
docs = fetch_20newsgroups(subset='all')['data']

# Fit the BERTopic model
topic_model = BERTopic()
topics, _ = topic_model.fit_transform(docs)

# Extract topics and their top words
topic_words = topic_model.get_topics()

# Calculate word and word-pair frequencies
word_freq = FreqDist()
pair_freq = FreqDist()

for doc in docs:
    words = doc.split()
    word_freq.update(words)
    pair_freq.update(bigrams(words))

total_docs = len(docs)

# Function to calculate PMI
def calculate_pmi(word_i, word_j):
    p_i = word_freq[word_i] / total_docs
    p_j = word_freq[word_j] / total_docs
    p_ij = pair_freq[(word_i, word_j)] / total_docs
    if p_ij > 0:
        return log(p_ij / (p_i * p_j))
    else:
        return 0

# Function to calculate NPMI
def calculate_npmi(word_i, word_j):
    p_ij = pair_freq[(word_i, word_j)] / total_docs
    if p_ij > 0:
        pmi = calculate_pmi(word_i, word_j)
        return pmi / -log(p_ij)
    else:
        return 0

# Calculate NPMI for each topic
topic_npmi = []
for topic, words in topic_words.items():
    npmi_values = []
    for i in range(len(words)):
        for j in range(i + 1, len(words)):
            npmi = calculate_npmi(words[i][0], words[j][0])
            npmi_values.append(npmi)
    if npmi_values:
        topic_npmi.append(np.mean(npmi_values))

# Calculate overall NPMI for the model
overall_npmi = np.mean(topic_npmi)
print(f"Overall NPMI: {overall_npmi}")
