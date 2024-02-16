from flask import Flask, render_template
from pyvis.network import Network
import networkx as nx
import io
from pyvis.network import Network
from helpers.test_test import test_me

app = Flask(__name__)

@app.route('/')
def index():
    test_me()
    '''
    G = nx.Graph()

    ## Add nodes to the graph
    G.add_node(
        "test")
    

## Add edges to the graph
    G.add_edge(
        str("node_1"),
        str("node_2"),
        title="edge",
    weight=1)

    G.add_edge(
        str("node_1"),
        str("node_2"),
        title="edge",
    weight=5)

    graph_output_directory = "./templates/index.html"

    net = Network(
        notebook=False,
        # bgcolor="#1a1a1a",
        cdn_resources="remote",
        height="900px",
        width="100%",
        select_menu=True,
        # font_color="#cccccc",
        filter_menu=False,
    )

    net.from_nx(G)
    net.force_atlas_2based(central_gravity=0.015, gravity=-31)
    net.show_buttons(filter_=["physics"])
    net.show(graph_output_directory) #notebook=False)
'''
    # Render the Pyvis graph to HTML
    #html = net.get_html()



    # Render the Flask template with the HTML content
    return  render_template('index.html') #render_template_string('<!DOCTYPE html>{{ html|safe }}</html>', html=html)

if __name__ == '__main__':
    app.run(debug=True)
