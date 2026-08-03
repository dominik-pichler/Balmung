import pandas as pd
from pyvis.network import Network

# Load nodes
nodes_df = pd.read_csv('nodes.csv')

# Load edges with weights
edges_df = pd.read_csv('edges.csv')

# Convert data types
nodes_df['node_id'] = nodes_df['node_id'].astype(str)
edges_df['source'] = edges_df['source'].astype(str)
edges_df['target'] = edges_df['target'].astype(str)
edges_df['weight'] = edges_df['weight'].astype(float)  # Convert to float for weights

# Set the number of top connections you want
N = 10  # Modify as needed

# Sort edges by weight and select the top N connections
top_connections = edges_df.nlargest(N, 'weight')

# Initialize a Pyvis Network
net = Network(notebook=True)

# Add nodes
for index, row in nodes_df.iterrows():
    net.add_node(row['node_id'], label=row['node_label'])

# Add only the top N edges with weights
for index, row in top_connections.iterrows():
    net.add_edge(row['source'], row['target'], value=row['weight'])

# Generate the visualization
net.show('network.html')