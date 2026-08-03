import csv
import os
import torch
from transformers import pipeline, AutoModelForQuestionAnswering, AutoTokenizer
from transformers.pipelines import QuestionAnsweringPipeline
import pandas as pd
import pickle
from typing import List, Dict
from tqdm import tqdm
from core_metrics import compute_f1, compute_exact

def load_model() -> QuestionAnsweringPipeline:
    model_name = "bert-large-uncased-whole-word-masking-finetuned-squad"
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Using device: {device}")

    model = AutoModelForQuestionAnswering.from_pretrained(model_name).to(device)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    qa_pipeline = pipeline("question-answering", model=model, tokenizer=tokenizer, device=0 if device == "mps" else -1)
    return qa_pipeline

def run_inference(qa_pipeline: QuestionAnsweringPipeline, query: str, passage: str) -> str:
    inputs = {"question": str(query), "context": str(passage)}
    result = qa_pipeline(inputs)
    return result['answer']

def save_checkpoint(results: List[Dict[str, str]], checkpoint_path: str):
    with open(checkpoint_path, 'wb') as f:
        pickle.dump(results, f)

def load_checkpoint(checkpoint_path: str) -> List[Dict[str, str]]:
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, 'rb') as f:
            results = pickle.load(f)
        return results
    return []

def process_fira_files(qa_pipeline: QuestionAnsweringPipeline, answers_file: str, tuples_file: str, checkpoint_path: str, checkpoint_path_IR: str) -> (List[Dict[str, str]], List[Dict[str, str]]):
    results = load_checkpoint(checkpoint_path)
    results_IR = load_checkpoint(checkpoint_path_IR)
    processed_queries = {(res['queryid'], res['documentid']) for res in results}
    processed_queries_IR = {(res['queryid'], res['documentid']) for res in results_IR}

    answers_df = pd.read_csv(answers_file, delimiter='\t')
    df = pd.read_csv(tuples_file, sep='\t', usecols=[0, 1, 2, 3, 4, 5], names=['queryid', 'documentid', 'relevance', 'query_text', 'document_text', 'text_selection'], header=None)

    # Ensure correct column types for merging
    answers_df['query_id'] = answers_df['query_id'].astype(str)
    answers_df['doc_id'] = answers_df['doc_id'].astype(str)
    df['queryid'] = df['queryid'].astype(str)
    df['documentid'] = df['documentid'].astype(str)

    # Merging answers with the tuple queries and documents
    merged_df_answers = pd.merge(answers_df, df[['queryid', 'query_text']], left_on='query_id', right_on='queryid', how='left').drop_duplicates()
    merged_df_answers = pd.merge(merged_df_answers, df[['documentid', 'document_text']], left_on='doc_id', right_on='documentid', how='left').drop_duplicates()

    # Intersection of Query IDs for evaluation
    common_ids = pd.merge(merged_df_answers[['query_id']], df[['queryid']], left_on='query_id', right_on='queryid', how='inner')[['query_id']].drop_duplicates()
    filtered_answers_df = merged_df_answers[merged_df_answers['query_id'].isin(common_ids['query_id'])]
    filtered_tuples_df = df[df['queryid'].isin(common_ids['query_id'])]

    for _, row in tqdm(filtered_answers_df.iterrows(), total=filtered_answers_df.shape[0]):
        query_id = row['queryid']
        document_id = row['documentid']
        query = row['query_text']
        passage = row['document_text']
        if (query_id, document_id) not in processed_queries_IR:
            answer = run_inference(qa_pipeline, query, passage)
            results_IR.append({'query_text': query, 'queryid': query_id, 'documentid': document_id, 'answer': answer, 'text_selection': row['document_text']})
            if len(results_IR) % 100 == 0:
                save_checkpoint(results_IR, checkpoint_path_IR)

    for _, row in tqdm(filtered_tuples_df.iterrows(), total=filtered_tuples_df.shape[0]):
        query_id = row['queryid']
        document_id = row['documentid']
        if (query_id, document_id) not in processed_queries:
            query = row['query_text']
            passage = row['document_text']
            answer = run_inference(qa_pipeline, query, passage)
            results.append({'query_text': query, 'queryid': query_id, 'documentid': document_id, 'answer': answer, 'text_selection': row['text_selection']})
            if len(results) % 100 == 0:
                save_checkpoint(results, checkpoint_path)

    save_checkpoint(results, checkpoint_path)
    save_checkpoint(results_IR, checkpoint_path_IR)
    return results, results_IR

if __name__ == "__main__":
    qa_pipeline = load_model()
    answers_file = "../data/msmarco_predictions_qa-answer-top1.txt"
    tuples_file = "../data/msmarco-fira-21.qrels.qa-tuples.tsv"
    checkpoint_path = "../data/checkpoint.pkl"
    checkpoint_path_IR = "../data/checkpoint_IR.pkl"

    results, results_IR = process_fira_files(qa_pipeline, answers_file, tuples_file, checkpoint_path, checkpoint_path_IR)
    df_results = pd.DataFrame(results)
    df_results.to_csv("../data/123_results_msmarco-fira-21.qa.csv", index=False)

    answers_gold = [res['answer'] for res in results]
    answers_pred = [res['answer'] for res in results_IR]

    f1_scores = [compute_f1(gold, pred) for gold, pred in zip(answers_gold, answers_pred)]
    exact_scores = [compute_exact(gold, pred) for gold, pred in zip(answers_gold, answers_pred)]

    avg_f1_score = sum(f1_scores) / len(f1_scores)
    avg_exact_score = sum(exact_scores) / len(exact_scores)

    print(f"Average F1 Score: {avg_f1_score}")
    print(f"Average Exact Score: {avg_exact_score}")
