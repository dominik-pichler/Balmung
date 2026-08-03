import sys
import polars as pl
import pandas as pd


def r2_score(df: pd.DataFrame) -> float:
    """
    Calculate the R^2 score as a measure of how reliable the judgements of each
    user are.

    Args:
        df (pd.DataFrame): The DataFrame containing the relevance levels and the
            mean relevance levels for each query-document pair.

    Returns:
        float: The R^2 score.
    """

    return pd.Series({
        'r2': 1 - ((df['meanRelevanceLevel'] - df['relevanceLevel']) ** 2).sum() / ((df['meanRelevanceLevel'] - df['meanRelevanceLevel'].mean()) ** 2).sum()
    })


def aggregate_judgements(source: str, target: str) -> None:
    """
    Aggregate the judgements from the source file and write the aggregated
    judgements to the target file.

    Args:
        source (str): The path to the source file containing the judgements.
        target (str): The path to the target file where the aggregated judgements
            should be written.
    """

    # Read the judgements from the source file and convert the relevance levels to integers
    judgements = (pd
        .read_csv(source, sep='\t')
        .assign(relevanceLevel=lambda x: x['relevanceLevel'].str.slice(0, 1).astype(int))
    )

    # Calculate the mean relevance levels for each query-document pair
    meanRelevanceLevels = (judgements
        .groupby(['queryId', 'documentId'])
        .agg({'relevanceLevel': 'mean'})
        .rename(columns={'relevanceLevel': 'meanRelevanceLevel'})
        .reset_index()
    )

    # Split the mean relevance levels into tied and non-tied when the judgements
    # do not lean towards a relevance level
    tied = (meanRelevanceLevels
        .query('meanRelevanceLevel % 1 == 0.5')
        .drop('meanRelevanceLevel', axis=1)
    )

    # Calculate the R^2 value as a measure of how reliable the judgements of
    # each user are.
    # We interpret the mean relevance level as the true value and the relevance
    # level of each judgement as the estimated value.
    userReliabilityScores = (judgements
        .merge(meanRelevanceLevels, on=['queryId', 'documentId'], how='inner')
        .groupby('userId')
        .apply(r2_score)
        .reset_index()
    )
    userReliabilityScores['r2'] = userReliabilityScores['r2'].clip(0, 1)

    # Select the relevance levels for the non-tied query-document pairs by rounding
    # the mean relevance levels to the nearest integer.
    selection = (meanRelevanceLevels
        .merge(tied, on=['queryId', 'documentId'], how='outer', indicator=True)
        .query('_merge == "left_only"')
        .assign(relevanceLevel=lambda x: x['meanRelevanceLevel'].round().astype(int))
        .drop(['meanRelevanceLevel', '_merge'], axis=1)
    )

    # Select the relevance levels for the tied query-document pairs by calculating
    # the weighted mean of the relevance levels based on the users reliability
    # scores.
    selectionForTied = (judgements
        .merge(tied, on=['queryId', 'documentId'], how='inner')
        .merge(userReliabilityScores, on='userId')
        .groupby(['queryId', 'documentId'])
        .apply(lambda x: pd.Series({
            'relevanceLevel': (x['r2'] * x['relevanceLevel']).sum() / x['r2'].sum()
        }))
        .reset_index()
        .assign(relevanceLevel=lambda x: x['relevanceLevel'].round().astype(int))
    )

    # Concatenate the selected relevance levels for the tied and non-tied
    # query-document pairs.
    result = (pd
        .concat([selection, selectionForTied], axis=0)
        .assign(Q0='Q0')
    )[['queryId', 'Q0', 'documentId', 'relevanceLevel']]

    # Write the aggregated judgements to the target file
    result.to_csv(target, sep=' ', header=False, index=False)


if __name__ == '__main__':
    """
    Aggregate the judgements from the source file and write the aggregated
    judgements to the target file.

    Usage:
        python src/judgement_aggregation.py <source> <target>
    """

    aggregate_judgements(sys.argv[1], sys.argv[2])