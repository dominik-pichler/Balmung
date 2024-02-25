#!/usr/bin/env python
# coding: utf-8

# In[3]:


pip install pymed


# In[23]:


import pandas as pd

pubmed = PubMed(tool="PubMedSearcher", email="myemail@ccc.com")

## PUT YOUR SEARCH TERM HERE ##
search_term = "Asthma"
results = pubmed.query(search_term, max_results=500)
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
    articleInfo.append({u'pubmed_id':pubmedId,
                       u'title':article['title'],
                       u'publication_date':article['publication_date'],
                       #u'journal':article['journal'],
                       u'abstract':article['abstract'],
                       u'conclusions':article['journal'],
                       #u'methods':article['methods'],
                       #u'results': article['results'],
                       #u'copyrights':article['copyrights'],
                       #u'doi':article['doi'],
                       u'authors':article['authors']})

# Generate Pandas DataFrame from list of dictionaries
articlesPD = pd.DataFrame.from_dict(articleInfo)
export_csv = articlesPD.to_csv (r'/Users/dominikpichler/Documents/Pet Projects/Athene/paper_export/test.csv', index = None, header=True) 

#Print first 10 rows of dataframe
print(articlesPD.head(10))


# In[27]:


import pandas as pd

pubmed = PubMed(tool="PubMedSearcher", email="myemail@ccc.com")

## PUT YOUR SEARCH TERM HERE ##
search_term = "Asthma"
results = pubmed.query(search_term, max_results=500)
articleList = []
articleInfo = []

for article in results:
# Print the type of object we've found (can be either PubMedBookArticle or PubMedArticle).
# We need to convert it to dictionary with available function
    articleDict = article.toDict()
    articleList.append(articleDict)

# Generate list of dict records which will hold all article details that could be fetch from PUBMED API
for article in articleList:
    conclusions = None

#Sometimes article['pubmed_id'] contains list separated with comma - take first pubmedId in that list - thats article pubmedId
    pubmedId = article['pubmed_id'].partition('\n')[0]
    # Append article info to dictionary 

    try:
        if article['conclusions'] is not None:
        # Assign 'conclusions' value if not None
            conclusions = article['conclusions']  
    except:
        print("no conclusion")  

    articleInfo.append({u'pubmed_id':pubmedId,
                       u'title':article['title'],
                       u'publication_date':article['publication_date'],
                       #u'journal':article['journal'],
                       u'abstract':article['abstract'],
                       u'conclusions': conclusions,
                       #u'methods':article['methods'],
                       #u'results': article['results'],
                       #u'copyrights':article['copyrights'],
                       #u'doi':article['doi'],
                       u'authors':article['authors']})

# Generate Pandas DataFrame from list of dictionaries
articlesPD = pd.DataFrame.from_dict(articleInfo)
export_csv = articlesPD.to_csv (r'/Users/dominikpichler/Documents/Pet Projects/Athene/paper_export/test.csv', index = None, header=True) 

#Print first 10 rows of dataframe
print(articlesPD.head(10))


# In[ ]:




