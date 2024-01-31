import spacy

# Load the English NLP model
nlp = spacy.load("en_core_web_sm")

# Process the text
text = "John works at a company called XYZ. He lives in New York."
doc = nlp(text)

# Extract entities and relationships
entities = [ent.text for ent in doc.ents]
relationships = [(ent.text, ent.root.head.text) for ent in doc.ents]

# Create nodes and edges
nodes = set(entities)
edges = set(relationships)

print("Nodes:", nodes)
print("Edges:", edges)
