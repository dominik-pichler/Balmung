from py2neo import Graph, Node, Relationship
import pandas as pd

graph = Graph("bolt://localhost:7687", auth=("neo4j", "12345678"))

def store_df_to_neo4j(df:DataFrame) -> Exception: 
    try:
        for index, row in df.iterrows():
            node1 = Node("Node", name=row['node3'])  # Assuming your node label is "Node"
            node2 = Node("Node", name=row['node4'])
            relationship_type = row['relationship']
            relationship = Relationship(node1, relationship_type, node2)
            graph.create(node1 | node2 | relationship)
            return None

    except:
        return Exception



if __name__ == '__main__':
    