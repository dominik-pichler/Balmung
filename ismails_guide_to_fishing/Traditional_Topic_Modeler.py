import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation, TruncatedSVD, NMF

# Example documents
documents = [
    'I love programming in Python.',
    'Python is great for data science.',
    'I love data science and machine learning.',
    'Machine learning is a fascinating field.',
]

# Create a document-term matrix using CountVectorizer for LDA
count_vectorizer = CountVectorizer()
term_matrix = count_vectorizer.fit_transform(documents)

# LDA Model
lda = LatentDirichletAllocation(n_components=2, random_state=0)
lda.fit(term_matrix)

print("LDA Topics:")
for idx, topic in enumerate(lda.components_):
    print(f'Topic {idx + 1}:')
    print([count_vectorizer.get_feature_names_out()[i] for i in topic.argsort()[-5:]])

# Create a document-term matrix using TF-IDF for LSA and NMF
tfidf_vectorizer = TfidfVectorizer()
tfidf_matrix = tfidf_vectorizer.fit_transform(documents)

# LSA Model
lsa = TruncatedSVD(n_components=2, random_state=0)
lsa.fit(tfidf_matrix)

print("\nLSA Topics:")
for idx, topic in enumerate(lsa.components_):
    print(f'Topic {idx + 1}:')
    print([tfidf_vectorizer.get_feature_names_out()[i] for i in topic.argsort()[-5:]])

# NMF Model
nmf = NMF(n_components=2, random_state=0)
nmf.fit(tfidf_matrix)

print("\nNMF Topics:")
for idx, topic in enumerate(nmf.components_):
    print(f'Topic {idx + 1}:')
    print([tfidf_vectorizer.get_feature_names_out()[i] for i in topic.argsort()[-5:]])