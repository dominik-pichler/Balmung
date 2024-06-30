import logging
import time
from transformers import pipeline, BertTokenizer, BertForSequenceClassification
import torch
import json

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load pre-trained BERT model for NER
logger.info("Loading NER model...")
ner_pipeline = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english")

# Load pre-trained BERT model and tokenizer for RE
logger.info("Loading RE model and tokenizer...")
re_model = BertForSequenceClassification.from_pretrained('bert-base-uncased')
re_tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')

# Example text
text = "John Doe works at OpenAI in San Francisco."

# Step 1: Perform NER
logger.info("Performing Named Entity Recognition...")
start_time = time.time()
entities = ner_pipeline(text)
logger.info(f"Named Entities: {entities}")
logger.info(f"NER took {time.time() - start_time:.2f} seconds")


# Function to merge broken entities
def merge_entities(entities):
    merged_entities = []
    current_entity = None

    for entity in entities:
        if entity['word'].startswith("##"):
            if current_entity:
                current_entity['word'] += entity['word'][2:]
                current_entity['end'] = entity['end']
                current_entity['score'] = min(current_entity['score'], entity['score'])
        else:
            if current_entity:
                merged_entities.append(current_entity)
            current_entity = {
                'entity': entity['entity'],
                'score': float(entity['score']),
                'word': entity['word'],
                'start': entity['start'],
                'end': entity['end']
            }

    if current_entity:
        merged_entities.append(current_entity)

    return merged_entities


# Merge broken entities
merged_entities = merge_entities(entities)
logger.info(f"Merged Entities: {merged_entities}")

# Extract unique entities
unique_entities = list({entity['word'] for entity in merged_entities})
logger.info(f"Unique Entities: {unique_entities}")


# Step 2: Perform Relation Extraction
def extract_relationships(text, entities):
    relationships = []
    for i, entity1 in enumerate(entities):
        for j, entity2 in enumerate(entities):
            if i < j:  # Avoid repeating pairs
                # Create input for RE model
                re_input_text = f"[CLS] {text} [SEP] {entity1} [SEP] {entity2} [SEP]"
                inputs = re_tokenizer(re_input_text, return_tensors="pt")

                # Predict relationship
                outputs = re_model(**inputs)
                logits = outputs.logits
                predicted_class = torch.argmax(logits, dim=1).item()

                # Add to relationships list
                relationships.append({
                    'entity1': entity1,
                    'entity2': entity2,
                    'relationship': predicted_class  # Replace with actual class label if available
                })
    return relationships


logger.info("Performing Relation Extraction...")
start_time = time.time()
relationships = extract_relationships(text, unique_entities)
logger.info(f"Relationships: {relationships}")
logger.info(f"Relation Extraction took {time.time() - start_time:.2f} seconds")

# Display the results in a readable format
#print("Named Entities:", json.dumps(merged_entities, indent=4))
#print("Unique Entities:", json.dumps(unique_entities, indent=4))
#print("Relationships:", json.dumps(relationships, indent=4))
