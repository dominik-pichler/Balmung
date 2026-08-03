from typing import Dict, Iterator, List

import torch
import torch.nn as nn
from torch.autograd import Variable

from allennlp.modules.text_field_embedders import TextFieldEmbedder
from allennlp.modules.matrix_attention.cosine_matrix_attention import CosineMatrixAttention
from allennlp.nn.util import add_positional_features


class TK(nn.Module):
    '''
    Paper: S. Hofstätter, M. Zlabinger, and A. Hanbury 2020. Interpretable & Time-Budget-Constrained Contextualization for Re-Ranking. In Proc. of ECAI 
    '''

    def __init__(self,
                 word_embeddings: TextFieldEmbedder,
                 n_kernels: int,
                 n_layers:int,
                 n_tf_dim:int,
                 n_tf_heads:int):

        super(TK, self).__init__()

        self.word_embeddings = word_embeddings

        # static - kernel size & magnitude variables
        mu = torch.FloatTensor(self.kernel_mus(n_kernels)).view(1, 1, 1, n_kernels)
        sigma = torch.FloatTensor(self.kernel_sigmas(n_kernels)).view(1, 1, 1, n_kernels)

        self.register_buffer('mu', mu)
        self.register_buffer('sigma', sigma)

        #todo

        """
        1. set transformer encoding layers with dim+heads from parameters
            - dropout set to 0 as in the GitHub-repository (in this file, with "repo" always referring to https://github.com/CaRniFeXeR/transformer-kernel-ranking/blob/master/matchmaker/models/tk_native.py)
            - dim_feedforward=n_tf_dim*4 because this was done in the orginal attention-paper
              to capture more complex relationships during the training"""
        encoder_layer = nn.TransformerEncoderLayer(n_tf_dim, n_tf_heads, dim_feedforward=n_tf_dim*4, dropout=0)
        self.contextualizer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers, norm=None)

        """
        2. CosineMatrix as in the repo
        """
        self.cosine_module = CosineMatrixAttention()


        """
        3. Linear layers as in the repo (bias also set to False)
        """
        self.dense = nn.Linear(n_kernels, 1, bias=False)
        self.dense_mean = nn.Linear(n_kernels, 1, bias=False)
        self.dense_comb = nn.Linear(2, 1, bias=False)

        """
        4. fill weights of those layers with small random weight values 
            drawn from a uniform distribution
        """
        torch.nn.init.uniform_(self.dense.weight, -0.014, 0.014)
        torch.nn.init.uniform_(self.dense_mean.weight, -0.014, 0.014)
        torch.nn.init.uniform_(self.dense_comb.weight, -0.014, 0.014)


    def forward(self, query: Dict[str, torch.Tensor], document: Dict[str, torch.Tensor]) -> torch.Tensor:
        # pylint: disable=arguments-differ

        #
        # prepare embedding tensors & paddings masks
        # -------------------------------------------------------

        # shape: (batch, query_max)
        query_pad_oov_mask = (query["tokens"]["tokens"] > 0).float() # > 1 to also mask oov terms
        # shape: (batch, doc_max)
        document_pad_oov_mask = (document["tokens"]["tokens"] > 0).float()

        # shape: (batch, query_max,emb_dim)
        query_embeddings = self.word_embeddings(query)
        # shape: (batch, document_max,emb_dim)
        document_embeddings = self.word_embeddings(document)

        #todo

        """
        1. apply transformers embedded queries and documents
            - transpose is used to align the dimensions of nn.TransformerEncoder 
              and the input tensor shape
            - the bitwise operator (~) is applied to reverse the boolean values of the mask
              to correctly the mask the desired tokens (True in the mask-tensor needs to be 
              False in the input of this method to be masked)
        """
        query_embeddings_context = self.contextualizer(add_positional_features(query_embeddings).transpose(1,0),src_key_padding_mask=~query_pad_oov_mask.bool()).transpose(1,0)
        document_embeddings_context = self.contextualizer(add_positional_features(document_embeddings).transpose(1,0),src_key_padding_mask=~document_pad_oov_mask.bool()).transpose(1,0)

        """
        2. apply masking to the query and document embeddings
            as preparation for the weighted sum
            - add 1 dimension to the mask to match [batch_size, sequence_length, embedding_dim]
        """
        query_embeddings = query_embeddings * query_pad_oov_mask.unsqueeze(-1)
        document_embeddings = document_embeddings * document_pad_oov_mask.unsqueeze(-1)

        """
        3. create weighted sum of word embeddings and contextualized embeddings
            - apply mask again because the addition could introduce non-zero values
              at masked positions
            - add 1 dimension to the mask again as in previous step
        """
        query_embeddings = (0.5 * query_embeddings + 0.5 * query_embeddings_context) * query_pad_oov_mask.unsqueeze(-1)
        document_embeddings = (0.5 * document_embeddings + 0.5 * document_embeddings_context) * document_pad_oov_mask.unsqueeze(-1)


        """
        4. perform batch matrix multiplication - prepare embedding tensors & paddings masks
            - create the relation between the valid tokens 
              and queries by using the padded masks
        """
        query_by_doc_mask = torch.bmm(query_pad_oov_mask.unsqueeze(-1), document_pad_oov_mask.unsqueeze(-1).transpose(-1, -2))
        query_by_doc_mask_view = query_by_doc_mask.unsqueeze(-1)

        """
        5. apply cosine similarity "attention" of queries and documents
            - apply mask from step before to keep relevant tokens
        """
        cosine_matrix = self.cosine_module.forward(query_embeddings, document_embeddings)
        cosine_matrix_masked = cosine_matrix * query_by_doc_mask
        cosine_matrix_extradim = cosine_matrix_masked.unsqueeze(-1)

        """
        6. apply gaussian kernel 
            - used to calculate soft term frequency (soft-TF) in next step
        """
        raw_kernel_results = torch.exp(- torch.pow(cosine_matrix_extradim - self.mu, 2) / (2 * torch.pow(self.sigma, 2)))
        kernel_results_masked = raw_kernel_results * query_by_doc_mask_view

        """
        7. calculate soft-TF
            - per_kernel_query = relevance scores for each 
              query term accross all document terms
            - apply log transformation and normalization in
              order to smooth the results 
            - again, masks applied with same reasoning as above
            - get results per kernel
        """
        doc_lengths = torch.sum(document_pad_oov_mask, 1)
        per_kernel_query = torch.sum(kernel_results_masked, 2)
        log_per_kernel_query = torch.log2(torch.clamp(per_kernel_query, min=1e-10)) * 0.01
        log_per_kernel_query_masked = log_per_kernel_query * query_pad_oov_mask.unsqueeze(-1)
        per_kernel = torch.sum(log_per_kernel_query_masked, 1)

        """
        8. calculate normalized interaction scores between queries and documents
            - per_kernel_query_mean = aggregated kernel interaction scores (+1
              to account for documents with length 0)
            - log_per_kernel_query_mean = per_kernel_query_mean scaled by fixed
              hyperparameter
            - log_per_kernel_query_masked_mean is with applied padding mask
            - per_kernel_mean = aggregated kernel scores for each document
        """
        per_kernel_query_mean = per_kernel_query / (doc_lengths.view(-1,1,1) + 1)
        log_per_kernel_query_mean = per_kernel_query_mean * 0.01
        log_per_kernel_query_masked_mean = log_per_kernel_query_mean * query_pad_oov_mask.unsqueeze(-1)
        per_kernel_mean = torch.sum(log_per_kernel_query_masked_mean, 1)

        """
        9. connect kernels with learned weights to create output
            - concatenate the 2 transformed tensors to shape [batch_size, 2]
              and squeeze final result
        """
        dense_out = self.dense(per_kernel)
        dense_mean_out = self.dense_mean(per_kernel_mean)
        dense_comb_out = self.dense_comb(torch.cat([dense_out,dense_mean_out],dim=1))
        output = torch.squeeze(dense_comb_out, 1)

        return output

    def kernel_mus(self, n_kernels: int):
        """
        get the mu for each guassian kernel. Mu is the middle of each bin
        :param n_kernels: number of kernels (including exact match). first one is exact match
        :return: l_mu, a list of mu.
        """
        l_mu = [1.0]
        if n_kernels == 1:
            return l_mu

        bin_size = 2.0 / (n_kernels - 1)  # score range from [-1, 1]
        l_mu.append(1 - bin_size / 2)  # mu: middle of the bin
        for i in range(1, n_kernels - 1):
            l_mu.append(l_mu[i] - bin_size)
        return l_mu

    def kernel_sigmas(self, n_kernels: int):
        """
        get sigmas for each guassian kernel.
        :param n_kernels: number of kernels (including exactmath.)
        :param lamb:
        :param use_exact:
        :return: l_sigma, a list of simga
        """
        bin_size = 2.0 / (n_kernels - 1)
        l_sigma = [0.0001]  # for exact match. small variance -> exact match
        if n_kernels == 1:
            return l_sigma

        l_sigma += [0.5 * bin_size] * (n_kernels - 1)
        return l_sigma
