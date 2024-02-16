from flask import Flask
from pyvis.network import Network
import networkx as nx
import random

def test_me():
    G = nx.Graph()

    ## Add nodes to the graph
    G.add_node("test_s")

    ## Add edges to the graph
    G.add_edge(str("node_" + str(random.randint(0, 9))),
               str("node_" + str(random.randint(0, 9))),
               title="edge",
               weight=1)

    G.add_edge(str("node_" + str(random.randint(0, 9))),
               str("node_" + str(random.randint(0, 9))),
               title="edge",
               weight=5)

    graph_output_directory = "./templates/index.html"

    net = Network(notebook=False,
                  # bgcolor="#1a1a1a",
                  cdn_resources="remote",
                  height="900px",
                  width="100%",
                  select_menu=True,
                  # font_color="#cccccc",
                  filter_menu=False)

    net.from_nx(G)
    # net.repulsion(node_distance=150, spring_length=400)
    net.force_atlas_2based(central_gravity=0.015, gravity=-31)
    # net.barnes_hut(gravity=-18100, central_gravity=5.05, spring_length=380)
    net.show_buttons(filter_=["physics"])

    net.save_graph(graph_output_directory)  # Output to the specified directory

if __name__ == '__main__':
    test_me()
