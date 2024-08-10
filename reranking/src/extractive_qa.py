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
    """
    Load pre-trained QA model and tokenizer with MPS support if available.

    Returns:
        QuestionAnsweringPipeline: A HuggingFace QA pipeline.
    """
    model_name = "bert-large-uncased-whole-word-masking-finetuned-squad"

    # Check if MPS backend is available
    device = "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Using device: {device}")

    model = AutoModelForQuestionAnswering.from_pretrained(model_name).to(device)
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    qa_pipeline = pipeline("question-answering", model=model, tokenizer=tokenizer, device=0 if device == "mps" else -1)
    return qa_pipeline


def run_inference(qa_pipeline: QuestionAnsweringPipeline, query: str, passage: str) -> str:
    """
    Run inference to get answers from the model.
    Generally speaking, the QA model can extract relevant answer phrases or sentences directly from a given context or passage of text.
    Due to understanding of semantic meaning they understand the semantic meaning of the question and can locate the position of the answer within the provided context.

    Hence, the input of the model consists of
        1. The question/query
        2. The relevant passage/document

    The model then extracts a answer and returns it.

    Args:
        qa_pipeline (QuestionAnsweringPipeline): The QA pipeline.
        query (str): The question/query.
        passage (str): The context passage.

    Returns:
        str: The answer predicted by the model.
    """
    inputs = {
        "question": str(query),
        "context": str(passage)
    }
    result = qa_pipeline(inputs)
    return result['answer']


def select_document(group):
    max_relevance = group['relevance'].max()
    max_docs = group[group['relevance'] == max_relevance]

    if len(max_docs) > 1:
        selected_doc = max_docs.sample(n=1).iloc[0]
    else:
        selected_doc = max_docs.iloc[0]

    return selected_doc


def save_checkpoint(results: List[Dict[str, str]], checkpoint_path: str):
    """
    Save the current state of results to a checkpoint file.

    Args:
        results (List[Dict[str, str]]): The current results.
        checkpoint_path (str): The path to save the checkpoint file.
    """
    with open(checkpoint_path, 'wb') as f:
        pickle.dump(results, f)


def load_checkpoint(checkpoint_path: str) -> List[Dict[str, str]]:
    """
    Load the results from a checkpoint file.

    Args:
        checkpoint_path (str): The path to the checkpoint file.

    Returns:
        List[Dict[str, str]]: The results loaded from the checkpoint.
    """
    if os.path.exists(checkpoint_path):
        with open(checkpoint_path, 'rb') as f:
            results = pickle.load(f)
        return results
    return []


def process_fira_files(qa_pipeline: QuestionAnsweringPipeline, answers_file: str, tuples_file: str,
                       checkpoint_path: str,checkpoint_path_IR:str) :
    """
    Process FiRA files and run inference on the data.

    Args:
        qa_pipeline (QuestionAnsweringPipeline): The QA pipeline.
        answers_file (str): Path to the MSMARCO FiRA answers file.
        tuples_file (str): Path to the MSMARCO FiRA tuples file.
        checkpoint_path (str): Path to save/load the checkpoint file.

    Returns:
        List[Dict[str, str]]: A list of dictionaries containing the results.
    """
    # Load checkpoint if it exists
    results = load_checkpoint(checkpoint_path)
    results_IR = load_checkpoint(checkpoint_path_IR)
    processed_queries = {(res['queryid'], res['documentid']) for res in results}
    processed_queries_IR = {(res['queryid'], res['documentid']) for res in results_IR}

    # Initialize an empty list to store the data



    answers_df = pd.read_csv(answers_file, delimiter='\t')

    # Create a DataFrame from the collected data

    tuple_data = []

    columns = ['queryid', 'documentid', 'relevance', 'query_text','document_text']

    # Read the first four columns using pandas
    df = pd.read_csv(tuples_file, sep='\t', usecols=[0, 1, 2, 3, 4], names=columns, header=None)


    tuples_df = df.groupby('queryid').apply(select_document).reset_index(drop=True)

    tuples_queries = tuples_df[['queryid', 'query_text']]
    tuples_document_text = df[['documentid', 'document_text']]

    # Convert columns to the same type before merging
    answers_df['query_id'] = answers_df['query_id'].astype(str)
    answers_df['doc_id'] = answers_df['doc_id'].astype(str)
    tuples_queries['queryid'] = tuples_queries['queryid'].astype(str)
    tuples_document_text['documentid'] = tuples_document_text['documentid'].astype(str)

    # merge query text
    merged_df_answers = pd.merge(answers_df, tuples_queries, left_on=['query_id'], right_on=["queryid"], how='left').drop_duplicates()[['query_id','doc_id','query_text']]

    #merge document text
    two_merged_df_answers = pd.merge(merged_df_answers, tuples_document_text, left_on=['doc_id'], right_on=["documentid"], how='left').dropna()

    # Find the intersection of Query IDs so we only compare queries that are in both sets in the end.

    two_merged_df_answers['query_id'] = two_merged_df_answers['query_id'].astype(str)
    tuples_df['queryid'] = tuples_df['queryid'].astype(str)

    common_ids = pd.merge(two_merged_df_answers[['query_id']], tuples_df[['queryid']], left_on='query_id', right_on='queryid',how='inner')[['query_id']].drop_duplicates()

    # Testing:
    filtered_answers_df = two_merged_df_answers[two_merged_df_answers['query_id'].isin(common_ids['query_id'])]
    filtered_tuples_df = tuples_df[tuples_df['queryid'].isin(common_ids['query_id'])]

    # Process top-1 neural re-ranking result (answers file)
    for _, row in tqdm(filtered_answers_df.iterrows()):
        query_id = row['query_id']
        document_id = row['doc_id']
        query = row['query_text']
        passage = row['document_text']

        if (query_id, document_id) not in processed_queries_IR:
            answer = run_inference(qa_pipeline, query, passage)
            results_IR.append(
                {'query_text': query,'query_id': query_id, 'doc_id': document_id, 'answer': answer,
                 'text_selection': row['document_text']})

            # Save checkpoint every 100 iterations
            if len(results_IR) % 100 == 0:
                save_checkpoint(results_IR, checkpoint_path_IR)

    # Process gold-label pairs (tuples file)
    for _, row in tqdm(filtered_tuples_df.iterrows()):
        query_id = row['queryid']
        document_id = row['documentid']
        if (query_id, document_id) not in processed_queries:
            query = row['query_text']
            passage = row['document_text']
            answer = run_inference(qa_pipeline, query, passage)
            results.append({'query_text': query,'queryid': query_id, 'documentid': document_id, 'answer': answer,
                            'document_text': row['document_text']})

            # Save checkpoint every 100 iterations
            if len(results) % 100 == 0:
                save_checkpoint(results, checkpoint_path)

    # Final save of checkpoint
    save_checkpoint(results, checkpoint_path)

    return results,results_IR


if __name__ == "__main__":
    # Load the model
    qa_pipeline = load_model()

    # Define file paths
    answers_file = "../data/msmarco_predictions_qa-answer-top1.txt"
    tuples_file = "../data/msmarco-fira-21.qrels.qa-tuples.tsv"
    checkpoint_path = "../data/checkpoint.pkl"
    checkpoint_path_IR  = "../data/checkpoint_IR.pkl"

    # Run inference and process files
    results,results_IR = process_fira_files(qa_pipeline, answers_file, tuples_file, checkpoint_path,checkpoint_path_IR)
    df_results = pd.DataFrame(results)
    df_results.to_csv("../data/123_results_msmarco-fira-21.qa.csv", index=False)


    #only evaluate the overlap of pairs that are in the result and the qrels) + the provided FiRA gold-label pairs
    # msmarco-fira-21.qrels.qa-tuples.tsv using the provided qa evaluation methods in core_metrics.py with the
    # MSMARCO-FiRA-2021 QA labels

    # Create Series from lists of answers
    answers_gold = pd.Series([res['answer'] for res in results], name='answer')
    answers_pred = pd.Series([res['answer'] for res in results_IR], name='answer')

    # Convert Series to DataFrames
    df_gold = answers_gold.to_frame()
    df_pred = answers_pred.to_frame()

    # Merge DataFrames on the common column
    merged_df_answers = pd.merge(df_gold, df_pred, left_index=True, right_index=True, suffixes=('_gold', '_pred'))

    f1_scores = [compute_f1(gold, pred) for gold, pred in zip(answers_gold, answers_pred)]
    exact_scores = [compute_exact(gold, pred) for gold, pred in zip(answers_gold, answers_pred)]

    avg_f1_score = sum(f1_scores) / len(f1_scores)
    avg_exact_score = sum(exact_scores) / len(exact_scores)

    print(avg_f1_score)
    print(avg_exact_score)
