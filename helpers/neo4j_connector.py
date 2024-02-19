from py2neo import Graph, Node, Relationship
import pandas as pd


graph = Graph("bolt://localhost:7687", auth=("neo4j", "your_password"))


# Assuming your DataFrame is named df
df = pd.DataFrame({
    'node1': [1, 2, 3],
    'node2': [4, 5, 6],
    'relationship': ['KNOWS', 'LIKES', 'FOLLOWS']
})


for index, row in df.iterrows():
    node1 = Node("Node", name=row['node1'])  # Assuming your node label is "Node"
    node2 = Node("Node", name=row['node2'])
    relationship_type = row['relationship']
    relationship = Relationship(node1, relationship_type, node2)
    graph.create(node1 | node2 | relationship)

