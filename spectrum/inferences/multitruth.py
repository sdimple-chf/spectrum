from spectrum.inferences.judge import Judge
from spectrum.models.triple import Triple
import collections
import math
import numpy as np
from scipy.special import comb

class MultiTruth(Judge):
    """
    This class implement our algorithm @cuong2017multitruth
    """
    def __init__(self):
        super().__init__()
        # number of false value in the underlying domain of any entity (subject,predicate)
        self.n = 10

        # default predicate degree (i.e., single-truth assumption
        self.default_degree = 1

    def fit(self, triples):
        super().index(triples)
        # probabilities
        self.entity_to_prior = [np.array([]) for i in range(self.nentities)]
        self.entity_to_marginal = np.zeros(self.nentities)
        self.entity_to_likelihood = [np.array([]) for i in range(self.nentities)]

        # source accuracy
        self.accuracy = np.ones(self.nsources)
        self.__compute_prior()
        self.__compute_source_accuracy()
        # self.__compute_likelihood()
        # self.__compute_marginal_likelihood()
        # self.__compute_posterior()
        # self.__compute_truth()

    def __compute_source_accuracy(self):
        """
        Compute the accuracy of each source: A(p) = sum(conf)/len(conf), where conf is the confidence vector
        of all triples provided by the source p.
        """
        for s in range(self.nsources):
            conf_vec = self.get_confidence(s)
            self.accuracy[s] = np.average(conf_vec)

    def get_confidence(self, source):
        """
        Get the confidences of all triples provided by a source

        Parameters
        ----------
        source: a source or a source index

        Returns
        -------
        a np.array of confidences
        """
        if isinstance(source, int):
            src_idx = source
        else:
            src_idx = self.sourceidx[source]
        result = np.array([])
        for e in range(self.nentities):
            src_indices = self.entity_to_srcs[e]
            src_mask = src_indices == src_idx
            conf_vec = self.entity_to_confs[e][src_mask]
            if (len(conf_vec) != 0):
                result = np.concatenate((result, conf_vec))
        return result

    def __compute_prior(self):
        """
        Compute prior of triples p(t). This prior is computed by average the confidence of all triples t that share
        the same t.fact, i.e., (subject,predicate,object)
        """
        print('computing prior P(t)...')
        for e in range(self.nentities):
            facts = self.entity_to_facts[e]
            fact_set = list(set(facts))
            conf_vec = self.entity_to_confs[e]
            prior = np.zeros(len(facts))
            for i in range(len(fact_set)):
                mask = facts == fact_set[i]
                prior[mask] = sum(conf_vec[mask])/len(conf_vec[mask])
            self.entity_to_prior[e] = prior
            print(self.entity[e], ' :', facts, self.entity_to_prior[e])

    def __compute_likelihood(self):
        pass

    def __compute_marginal_likelihood(self):
        """
        Compute marginal likelihood P(De), where De is the list of triples about entity e=(subject,predicate)
        print('computing marginal likelihood
        """
        print('computing marginal likelihood P(De)...')
        for e in range(self.nentities):
            # De
            facts = self.entity_to_facts[e]

            # set(De)
            fact_set = list(set(facts))

            # source accuracies
            accuracy = self.entity_to_srcs[e]

            #TODO: define self.degree and self.predicate
            self.entity_to_marginal[e] = self.compute_marginal(e, self.degree[self.predicate[e]])

    def compute_marginal(self, entity, degree):
        """
        Compute marginal likelihood
        """
        if isinstance(entity, int):
            e = entity
        else:
            e = self.entityidx[entity]

        # De
        facts = self.entity_to_facts[e]

        # set(De)
        fact_set = list(set(facts))

        # source accuracies
        accuracy = self.entity_to_srcs[e]

        # marginal likelihood P(De)
        marginal = np.zeros(len(facts))
        for mask in self.nchoosek_subset(len(fact_set), degree):
            marginal = marginal + self.compute_marginal_part(accuracy, degree, self.n)
        return marginal

    def compute_marginal_part(self, accuracy, mask, nfalse, degree):
        """
        Compute conditional marginal likelihood P(De|T)

        Parameters
        ----------
        accuracy: a list of source accuracy
        mask: a boolean np.array to determine which source provides true triple/false triple
        nfalse: the number false values in the underlying domain of predicate
        degree: the degree of the predicate

        Returns
        -------
        conditional marginal likelihood
        """
        marginal_part = np.zeros(len(accuracy))
        marginal_part[mask] = accuracy[mask]
        marginal_part[~mask] = (1 - accuracy[~mask]) / nfalse
        return marginal_part

    def __compute_posterior(self):
        pass

    def __compute_truth(self):
        pass

    def nchoosek_subset(self, n, k):
        """
        Generator of boolean vector of combination c(n,k): [0011] means pick the last 2 object from 4 objects.
        Implementation according to http://www.math.umbc.edu/~campbell/Computers/Python/probstat.html
             def fixeddensity(thelen, density):
            if thelen == density:
                yield [1] * thelen
            elif density == 0:
                yield [0] * thelen
            else:
                for leftlist in fixeddensity(thelen - 1, density):
                    yield leftlist + [0]
                for leftlist in fixeddensity(thelen - 1, density - 1):
                    yield leftlist + [1]

        If combinations are thought of as binary vectors we can write them in order, so
        0011 < 0101 < 0110 < 1001 < 1010 < 1100. From this we see that the vectors whose top bit is zero are listed
        first, then those with top bit equal to one. The vectors whose top bit is zero has bottom three bits whose density is two and the vectors whose top bit is one have bottom three bits whose density is one.
        """
        if n == k:
            yield [1] * n
        elif k == 0:
            yield [0] * n
        else:
            for leftlist in self.nchoosek_subset(n - 1, k):
                yield leftlist + [0]
            for leftlist in self.nchoosek_subset(n - 1, k - 1):
                yield leftlist + [1]

    def get_prior(self, fact):
        """
        return prior belief of a fact, i.e., a triple

        Parameters
        ----------
        fact: a triple (subject,predicate,object)

        Returns
        -------
        prior probility of this fact if it exists or None otherwise
        """
        eidx = self.entityidx[fact.entity]
        result = self.entity_to_prior[eidx][fact.object == self.entity_to_facts[eidx]]
        if (len(result) == 0):
            return None
        return result[0]