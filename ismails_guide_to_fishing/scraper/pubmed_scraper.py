import pandas as pd
from pymed import PubMed
import sqlite3
pubmed = PubMed(tool="PubMedSearcher", email="myemail@ccc.com")

def convert_authors(authors):
    if isinstance(authors, list):
        return ', '.join(author['name'] for author in authors if isinstance(author, dict) and 'name' in author)
    return authors

def fetch_latest_publications(search_term,start_date, end_date):
    '''

    :param search_term:
    :type search_term:
    :param start_date:
    :type start_date:
    :param end_date:
    :type end_date:
    :return:
    :rtype:
    '''

    query = f'(("{start_date}"[Date - Create] : "{end_date}"[Date - Create])) AND {search_term})'

    # Execute the query against the API
    results = pubmed.query(query, max_results=500)


    articleList = []
    articleInfo = []

    for article in results:
    # Print the type of object we've found (can be either PubMedBookArticle or PubMedArticle).
    # We need to convert it to dictionary with available function
        articleDict = article.toDict()
        articleList.append(articleDict)

    # Generate list of dict records which will hold all article details that could be fetch from PUBMED API
    for article in articleList:
    #Sometimes article['pubmed_id'] contains list separated with comma - take first pubmedId in that list - thats article pubmedId
        pubmedId = article['pubmed_id'].partition('\n')[0]
        # Append article info to dictionary
        print(article)
        articleInfo.append({
                u'pubmed_id': pubmedId,
                u'title': article.get('title', None),
                u'publication_date': article.get('publication_date', None),
                u'journal': article.get('journal', None),
                u'abstract': article.get('abstract', None),
                u'conclusions': article.get('conclusions', None),
                u'methods': article.get('methods', None),
                u'results': article.get('results', None),
                u'copyrights': article.get('copyrights', None),
                u'doi': article.get('doi', None),
                u'authors': article.get('authors', None)
        })


    conn = sqlite3.connect('../databases/articles.db')
    cursor = conn.cursor()

    # Create a table for article info
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS article_info (
        id INTEGER PRIMARY KEY,
        pubmed_id TEXT,
        title TEXT,
        publication_date TEXT,
        journal TEXT,
        abstract TEXT,
        conclusions TEXT,
        methods TEXT,
        results TEXT,
        copyrights TEXT,
        doi TEXT,
        authors TEXT
    )
    ''')

    # Insert articleInfo into the database
    for article in articleInfo:
        # Convert list of authors to a comma-separated string using the helper function
        authors_str = convert_authors(article.get('authors', []))

        cursor.execute('''
        INSERT INTO article_info (pubmed_id, title, publication_date, journal, abstract, conclusions, methods, results, copyrights, doi, authors)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                       (article.get('pubmed_id'), article.get('title'), article.get('publication_date'),
                        article.get('journal'),
                        article.get('abstract'), article.get('conclusions'), article.get('methods'), article.get('results'),
                        article.get('copyrights'), article.get('doi'), authors_str))

    # Commit the transaction
    conn.commit()

    # Close the connection
    conn.close()


if __name__ == '__main__':

    search_term = "Asthma"
    start_date = "2018/05/01"
    end_date = "2018/05/02"

    fetch_latest_publications(search_term, start_date, end_date)