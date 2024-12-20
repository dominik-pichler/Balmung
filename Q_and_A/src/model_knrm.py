from typing import Dict, Iterator, List

import torch
import torch.nn as nn
from torch.autograd import Variable

from allennlp.modules.text_field_embedders import TextFieldEmbedder


class KNRM(nn.Module):
    '''
    Paper: End-to-End Neural Ad-hoc Ranking with Kernel Pooling, Xiong et al., SIGIR'17
    '''

    def __init__(self,
                 word_embeddings: TextFieldEmbedder,
                 n_kernels: int):

        super(KNRM, self).__init__()

        self.word_embeddings = word_embeddings

        # static - kernel size & magnitude variables
        mu = torch.FloatTensor(self.kernel_mus(n_kernels)).view(1, 1, 1, n_kernels)
        sigma = torch.FloatTensor(self.kernel_sigmas(n_kernels)).view(1, 1, 1, n_kernels)

        self.register_buffer('mu', mu)
        self.register_buffer('sigma', sigma)

        self.dense = nn.Linear(n_kernels, 1)

    def forward(self, query: Dict[str, torch.Tensor], document: Dict[str, torch.Tensor]) -> torch.Tensor:
        # pylint: disable=arguments-differ

        #
        # prepare embedding tensors & paddings masks
        # -------------------------------------------------------

        # shape: (batch, query_max)
        query_pad_oov_mask = (query["tokens"]["tokens"] > 0).float()  # > 1 to also mask oov terms

        # shape: (batch, doc_max)
        document_pad_oov_mask = (document["tokens"]["tokens"] > 0).float()

        # shape: (batch, query_max,emb_dim)
        query_embeddings = self.word_embeddings(query)
        # shape: (batch, document_max,emb_dim)
        document_embeddings = self.word_embeddings(document)

        # 1. Compute Interaction_matrix
        # Here we perform a barch matrix multiplication to capture the similarity between each query term and each
        # document term as it is the basis for the subsequent kernel pooling
        # Dimensions:
        # shape: (batch, query_max, doc_max)
        interaction_matrix = torch.bmm(query_embeddings, document_embeddings.transpose(1, 2))

        # Apply Kernel Pooling:
        # shape: (batch, query_max, doc_max, n_kernels)
        kernel_pooling = torch.exp(-0.5 * ((interaction_matrix.unsqueeze(-1) - self.mu) ** 2) / (self.sigma ** 2))

        # Sum over document dimension (pooling)
        # shape: (batch, query_max, n_kernels)
        kernel_sum = torch.sum(kernel_pooling * document_pad_oov_mask.unsqueeze(1).unsqueeze(-1), dim=2)

        # Log-sum-exp over query dimension
        # shape: (batch, n_kernels)
        log_pooling = torch.log(torch.clamp(kernel_sum, min=1e-10)) * query_pad_oov_mask.unsqueeze(-1)
        log_pooling_sum = torch.sum(log_pooling, dim=1)

        # Compute final score
        # shape: (batch_size, 1)
        output = self.dense(log_pooling_sum)

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
