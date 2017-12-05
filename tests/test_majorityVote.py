from unittest import TestCase

__author__ = 'totucuong'
__date__ = '12/5/17'

from spectrum.models.majority import MajorityVote
from spectrum.data.random import RandomData
from spectrum.data.population import Population


class TestMajorityVote(TestCase):
    def test_fit_random(self):
        claims = RandomData.generate()
        majority = MajorityVote()
        majority.fit(claims)
        resolves = majority.get_resolved_claims()
        assert resolves['obama|born_in'][0] == 'usa'

    def test_fit_population(self):
        population = Population(path_to_claims='../data/population/claims/population_claims.csv',
                            path_to_ground_truth='../data/population/ground_truth/population_truth.csv')
        majority = MajorityVote()
        majority.fit(population.claims)
        resolves = majority.get_resolved_claims()
        assert resolves['abu dhabi|Population2006'][0] == 1000230
