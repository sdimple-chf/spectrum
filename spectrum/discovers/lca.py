import numpy as np
import pyro
import pyro.distributions as dist
import torch


def simpleLCA(observation, confidence):
    """implement simpleLCA generative model.
    
    A claim is modeled as triple (source_id, object_id, value). This means the ``source_id`` asserts
    that the ``object_id`` takes on value ``value``.
    
    Parameters
    ----------
    observation: np.ndarray
    """
    pass


def build_mask(claims):
    """Build the mask matrix [w_so] of shape |S| * |O|, where S and O 
    are the set of sources and objects, respectively.
    
    We assume that the source_id are numbered from 0 to |S|-1. Similarly
    the objects are numbered from 0 to |O|-1.

    Parameters
    ----------
    claims: pd.DataFrame
        a data frame that has columns [source_id, object_id, value]
        
    Returns
    -------
    mask: np.ndarray
        a 2D array of shape (source, object) (w_so in the paper)
    """
    max_ids = claims.max()[['source_id', 'object_id']]
    n_sources = max_ids['source_id'] + 1
    n_objects = max_ids['object_id'] + 1
    W = np.zeros(shape=(n_sources, n_objects))

    def set_assertion(x):
        W[x.source_id, x.object_id] = 1

    claims.apply(lambda x: set_assertion(x), axis=1)
    return W.astype(int)


def build_observation(claims):
    """Build observation data structure out of `claims`.
    
    A dictionary mapping objects to a matrix of observations, (o -> [b_sc]), where b_sc = {0, 1}, 1 means 
    source s asserts c about object o, and 0 means s thinks c is wrong.
    
    Note that a source s does not need to make assertions about all objects. The superflous assertions b_sc
    is rendered useless using the mask W (see build_mask()).

    Also note that, we encode value (assertions a source about an object) as 
    categorical value and label encode them.

    Parameters
    ----------
    claims: pd.DataFrame
        a data frame that has columns [source_id, object_id, value]
        
    Returns
    -------
    observation: dict
        a dictionary mapping object o to its assertation maxtrix [b_sc]
    """
    max_ids = claims.max()
    n_sources = max_ids['source_id'] + 1
    n_objects = max_ids['object_id'] + 1

    observation = dict()

    def build_obs_matrix(df, object_id):
        """build matrix b_sc from a data frame
        
        Parameters
        ----------
        df: pd.DataFrame
            a data frame whose columns are [source_id, value]
        """
        n_values = df.max()['value'] + 1
        bsc = np.zeros(shape=(n_sources, n_values))

        def set_assertion(x):
            bsc[x['source_id'], x['value']] = 1

        df.apply(set_assertion, axis=1)
        observation[object_id] = bsc

    claims.groupby('object_id').apply(lambda x: build_obs_matrix(x, x.name))
    return observation


def lca_model(observation, mask):
    """Build a Latent Credibility Analysis (LCA).
   
    A LCA model represents a joint distribution p(Y, H, X), where
    Y represents hidden truth rvs, H represents data source honesty, and X
    represents observation.

    Concretely, let's assume that we have M objects, S data sources, and our
    observation will be the mask matrix W, `mask`, (see build_mask()), and
    observation matrix `observation` (see build_observation()).

    With this context, we have:
        p(Y, H, X) = product_{m=1,..,M}[p(y_m, H, X)], where
        p(y_m, H, X) = p(y_m)product_{s in S_m}[p(b_sm|y_m,s)p(s)],
        where S_m are the set of sources that make claims about an object m.

    @TODO: vectorize the implementation if possible.

    Parameters
    ----------
    observation: dict
        a dictionary of observation (o->[b_sc]). See build_observation() for
        details.

    mask: np.array
        a 2D array of shape (#sources, #objects)
    """
    n_sources, n_objects = mask.shape
    # create honest rv, H_s, for each sources
    honest = []
    for s in range(n_sources):
        honest.append(
            pyro.sample(
                f's_{s}',
                dist.Bernoulli(
                    pyro.param(f'theta_s_{s}',
                               init_tensor=torch.tensor(0.5)))))
    # creat hidden truth rv for each object m
    hidden_truth = []
    for m in range(n_objects):
        _, domain_size = observation[m].shape
        hidden_truth.append(
            pyro.sample(
                f'y_{m}',
                dist.Categorical(
                    probs=pyro.param(f'theta_m_{m}',
                                     init_tensor=1 / domain_size *
                                     torch.ones((domain_size, ))))))
    for m in range(n_objects):
        y_m = hidden_truth[m]
        _, domain_size = observation[m].shape
        for s in range(n_objects):
            theta_sm = ((1 - pyro.param(f'theta_s_{s}') /
                         (domain_size - 1))) * torch.ones((domain_size, ))
            theta_sm[y_m] = pyro.param(f'theta_s_{s}')
            pyro.sample(f'b_{s,m}', dist.Categorical(probs=theta_sm))


def bvi(simpleLCA_fn):
    """perform blackbox mean field variational inference on simpleLCA.
    
    This methods take a simpleLCA model as input and perform blackbox variational
    inference, and returns a list of posterior distributions of hidden truth and source
    reliability. 
    
    Concretely, if s is a source then posterior(s) is the probability of s being honest.
    And if o is an object, or more correctly, is a random variable that has the support as
    the domain of an object, then posterior(o) is the distribution over these support.
    The underlying truth value of an object could be computed as the mode of this
    distribution.
    
    Parameters
    ----------
    simpleLCA_fn: function
        a function that represents the simpleLCA generative models.
        
    Returns
    -------
    posteriors: list
        a list of posterior distributions of hidden truths and source reliability.
    """
    pass


def main():
    """We use the following example, taken from LCA paper, to test out
    all functions in this examples:

    2 objects: m1='obama's birth place', m2='obama's birthdate'.
    1 sources:  s1='John'.
    s1 asserts about m1: c1 = 'Obama was born in Haiwai'
    
    Suppose we have other assertions made by different sources about
    m1: 
        c2="Obama was born in Indonesia",
        c3="Obama was born in Kenya".

    Let's denote dom(m1) as m1's domain.

    We encode datasets as follows.

    sources = {0, 1, ... S-1}, S is the total number of sources
    object = {0, 1, ..., M-1}, M is the total number of objects
    for each object o=0,..,M-1, we encode dom(o) as {0,..., |dom(o)|-1}
    
    For "john", we encode him as s=0 and for object o, we have vector
    [1, 0, 0] to represent the fact that he asserts 'Obama was born
    in Hawai'.

    What about other objects that John does not make any assertions about?
    We can apply a mask W = [w_so] where s indices sources and o indices
    objects. w_so =1 if s makes assertion about o, otherwise 0.

    """
    import pandas as pd
    claims = dict()
    claims['source_id'] = [0, 0, 1]
    claims['object_id'] = [0, 1, 1]
    claims['value'] = [0, 1, 0]
    claims = pd.DataFrame(data=claims)


if __name__ == "__main__":
    main()
