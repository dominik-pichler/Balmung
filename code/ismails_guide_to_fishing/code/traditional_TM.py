import gensim
from gensim import corpora
from gensim.models import LdaModel, LsiModel, Nmf
from gensim.parsing.preprocessing import preprocess_string, strip_punctuation, strip_numeric, remove_stopwords
from gensim.models.coherencemodel import CoherenceModel
from bertopic import BERTopic



def print_topics(model, num_topics=2):
    for idx, topic in model.print_topics(num_topics=num_topics, num_words=5):
        print(f"Topic {idx}: {topic}")

def main():
    # Sample documents
    documents = [
        "Natural language processing with Gensim is fun.",
        "Topic modeling is a great way to understand text data.",
        "Natural language processing with Gensim is fun.",
        "Natural language processing with Gensim is fun.",
        "Natural language processing with Gensim is fun.",
        "Natural language processing with Gensim is fun.",
        "Natural language processing with Gensim is fun.",
        "Gensim supports many topic modeling algorithms.",
        "LDA, LSA, and NMF are popular topic models in Gensim.",
        'I enjoy analyzing text data',
    ]

    # Preprocess documents
    custom_filters = [strip_punctuation, strip_numeric, remove_stopwords]
    texts = [preprocess_string(doc, custom_filters) for doc in documents]

    # Create a dictionary and corpus
    dictionary = corpora.Dictionary(texts)
    corpus = [dictionary.doc2bow(text) for text in texts]

    # Train LDA model
    lda_model = LdaModel(corpus=corpus, id2word=dictionary, num_topics=2, random_state=42)

    # Train LSA model
    lsa_model = LsiModel(corpus=corpus, id2word=dictionary, num_topics=2)

    # Train NMF model
    nmf_model = Nmf(corpus=corpus, id2word=dictionary, num_topics=2, random_state=42)


    # Calculate NPMI coherence for each model
    lda_coherence_model_npmi = CoherenceModel(model=lda_model, texts=texts, dictionary=dictionary, coherence='c_npmi')
    lsa_coherence_model_npmi = CoherenceModel(model=lsa_model, texts=texts, dictionary=dictionary, coherence='c_npmi')
    nmf_coherence_model_npmi = CoherenceModel(model=nmf_model, texts=texts, dictionary=dictionary, coherence='c_npmi')

    lda_coherence_npmi = lda_coherence_model_npmi.get_coherence()
    lsa_coherence_npmi = lsa_coherence_model_npmi.get_coherence()
    nmf_coherence_npmi = nmf_coherence_model_npmi.get_coherence()

    # Results
    results = {
        'LDA': {'NPMI Coherence': lda_coherence_npmi},
        'LSA': {'NPMI Coherence': lsa_coherence_npmi},
        'NMF': {'NPMI Coherence': nmf_coherence_npmi}
    }
    print(results)

    # Uncomment the following line if you want to print the results
    # print(results)

if __name__ == '__main__':
    main()
