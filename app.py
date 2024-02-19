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
    # Render the Pyvis graph to HTML
    #html = net.get_html()



    # Render the Flask template with the HTML content
    return  render_template('index.html') #render_template_string('<!DOCTYPE html>{{ html|safe }}</html>', html=html)

if __name__ == '__main__':
    app.run(debug=True)
