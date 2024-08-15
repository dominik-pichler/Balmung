import sqlite3
from bertopic import BERTopic

# Connect to the SQLite database
db_path = '../databases/articles_Asthma.db'  # Change this to your database path
connection = sqlite3.connect(db_path)
cursor = connection.cursor()

# Fetching the 'Abstract' column
cursor.execute('SELECT abstract FROM article_info_long WHERE abstract IS NOT NULL AND ABSTRACT IS NOT "" LIMIT 50 ')  # Change your_table_name accordingly
abstracts = cursor.fetchall()

# Closing the connection
connection.close()

# Extracting abstracts from the fetched data
abstracts = [abstract[0] for abstract in abstracts if abstract[0] is not None]
print(f"Evaluating {len(abstracts)} papers")
# Initialize the BERTopic model
topic_model = BERTopic()

# Perform topic modeling on the extracted documents
topics, _ = topic_model.fit_transform(abstracts)

# Get the topic information
topic_info = topic_model.get_topic_info()
print(topic_info)
# Displaying the topics
print(topic_model.get_topic_info())

doc_info = topic_model.get_document_info(abstracts[0])
print(doc_info)

topic_model.visualize_barchart(top_n_topics = 16, n_words = 10)
