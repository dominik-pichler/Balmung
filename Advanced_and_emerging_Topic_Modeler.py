# BERTopic Example
from bertopic import BERTopic
from sklearn.datasets import fetch_20newsgroups

# Load the dataset
docs = fetch_20newsgroups(subset='all')['data']

# Create a BERTopic model
topic_model = BERTopic()

# Fit the model to the documents
topics, probabilities = topic_model.fit_transform(docs)

# Display the topics
print("BERTopic Topics:")
print(topic_model.get_topic_info())

# Top2Vec Example
from top2vec import Top2Vec

# Create a Top2Vec model
top2vec_model = Top2Vec(documents=docs, speed="learn", workers=4)

# Get the number of topics found
num_topics = top2vec_model.get_num_topics()

# Display the topics
print("\nTop2Vec Topics:")
for i in range(num_topics):
    print(f"Topic {i + 1}:")
    words, word_scores, topic_nums = top2vec_model.get_topics(i)
    print(words)