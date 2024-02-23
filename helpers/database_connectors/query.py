from py2neo import Graph

# Connect to the Neo4j database
graph = Graph("bolt://localhost:7687", auth=("neo4j", "12345678"))

# Define and execute the Cypher query for City nodes
query_all = """
MATCH (n)
RETURN n
"""
result_all = graph.run(query_all)

print((result_all))
# Print the result for City nodes
for record in result_all:
    print(record)
