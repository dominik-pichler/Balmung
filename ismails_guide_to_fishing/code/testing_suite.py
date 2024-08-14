import gensim
from gensim import corpora
from gensim.models import LdaModel, LsiModel, Nmf
from gensim.parsing.preprocessing import preprocess_string, strip_punctuation, strip_numeric, remove_stopwords

# Sample documents
documents = [
    "Natural language processing with Gensim is fun.",
    "Topic modeling is a great way to understand text data.",
    "Gensim supports many topic modeling algorithms.",
    "LDA, LSA, and NMF are popular topic models in Gensim."
]

# Preprocess documents
custom_filters = [strip_punctuation, strip_numeric, remove_stopwords]
texts = [preprocess_string(doc, custom_filters) for doc in documents]

# Create a dictionary and corpus
dictionary = corpora.Dictionary(texts)
corpus = [dictionary.doc2bow(text) for text in texts]

# Function to train and print topics from a model
def print_topics(model, num_topics=2):
    for idx, topic in model.print_topics(num_topics=num_topics, num_words=5):
        print(f"Topic {idx}: {topic}")

# Train LDA model
lda_model = LdaModel(corpus=corpus, id2word=dictionary, num_topics=2, random_state=42)
print("LDA Topics:")
print_topics(lda_model)

# Train LSA model
lsa_model = LsiModel(corpus=corpus, id2word=dictionary, num_topics=2)
print("\nLSA Topics:")
print_topics(lsa_model)

# Train NMF model
nmf_model = Nmf(corpus=corpus, id2word=dictionary, num_topics=2, random_state=42)
print("\nNMF Topics:")
print_topics(nmf_model)