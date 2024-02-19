# Import modules from neo4j library
from neo4j import GraphDatabase, basic_auth


# Establish connection with neo4j database, mention your host, port, username & password(default port is 7687 and default host is localhost)
driver = GraphDatabase.driver("bolt://localhost:7687", auth = basic_auth("neo4j","12345678"))


# create a neo4j session in python
session = driver.session(database = 'papers')


# store all the records(including nodes & relationships) in a list
cyper_query = """ CREATE (:Person {name: 'Alice', age: 30}) CREATE (:Person {name: 'Bob', age: 35})
CREATE (:Person {name: 'Charlie', age: 40})
CREATE (:Person {name: 'David', age: 25})
CREATE (:City {name: 'New York'})
CREATE (:City {name: 'Los Angeles'})
CREATE (:City {name: 'Chicago'})
CREATE (:City {name: 'San Francisco'})
CREATE (:City {name: 'Seattle'})
CREATE (:City {name: 'Boston'})
CREATE (:City {name: 'Denver'})
CREATE (:City {name: 'Austin'})
CREATE (:City {name: 'Atlanta'})
CREATE (:City {name: 'Miami'})
CREATE (:City {name: 'Houston'})
CREATE (:City {name: 'Philadelphia'})
CREATE (:City {name: 'Dallas'})
CREATE (:City {name: 'Phoenix'})
CREATE (:City {name: 'Las Vegas'})
CREATE (:City {name: 'Washington, D.C.'})
CREATE (:City {name: 'San Diego'})
CREATE (:City {name: 'Portland'})
CREATE (:City {name: 'Minneapolis'})
CREATE (:City {name: 'Detroit'})
CREATE (:City {name: 'San Antonio'})
CREATE (:City {name: 'Orlando'})

"""
records = list(session.run(cyper_query))


print(records)

driver.close()

