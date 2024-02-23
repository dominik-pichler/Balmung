from py2neo import Graph, Node, Relationship
import pandas as pd

graph = Graph("bolt://localhost:7687", auth=("neo4j", "12345678"))

def store_df_to_neo4j(df) -> Exception: 


    df.columns = ['Node1', 'Node2', 'Relationship']
    try:
        for index, row in df.iterrows():
            node1 = Node("Node", name=row['Node1'])  # Assuming your node label is "Node"
            node2 = Node("Node", name=row['Node2'])
            relationship_type = row['Relationship']
            relationship = Relationship(node1, relationship_type, node2)
            graph.create(node1 | node2 | relationship)
            return "Success"

    except Exception as e:
        print(e)
        return e



if __name__ == '__main__':
    data = {
        '1': ['Alice', 'Bob', 'Charlie', 'David'],
        '2': [25, 30, 35, 40],
        '3': ['New York', 'Los Angeles', 'Chicago', 'Houston']
    }  
    df = pd.DataFrame(data)
  

    print((store_df_to_neo4j(df)))