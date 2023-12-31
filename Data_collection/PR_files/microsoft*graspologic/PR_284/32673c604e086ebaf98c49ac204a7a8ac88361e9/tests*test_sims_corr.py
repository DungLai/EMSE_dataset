import unittest
from graspy.simulations.simulations_corr import sample_edges_corr, er_corr, sbm_corr
import numpy as np
import pytest
import warnings


class Test_Sample_Corr(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.n = 500
        cls.p = 0.5
        cls.r = 0.3
        cls.P = cls.p * np.ones((cls.n, cls.n))
        cls.R = cls.r * np.ones((cls.n, cls.n))

    def test_bad_input(self):
        with self.assertRaises(TypeError):
            P = 10
            sample_edges_corr(P, self.R, directed=False, loops=False)

        with self.assertRaises(TypeError):
            P = "0.5"
            sample_edges_corr(P, self.R, directed=False, loops=False)

        with self.assertRaises(TypeError):
            R = 10
            sample_edges_corr(self.P, R, directed=False, loops=False)

        with self.assertRaises(TypeError):
            R = "0.5"
            sample_edges_corr(self.P, R, directed=False, loops=False)

        with pytest.raises(TypeError):
            sample_edges_corr(self.P, self.r, directed="hey", loops=False)

        with pytest.raises(TypeError):
            sample_edges_corr(self.P, self.r, directed=False, loops=6)

    def test_sample_edges_corr(self):
        # P = self.p * np.ones((self.n, self.n))
        g1, g2 = sample_edges_corr(self.P, self.R, directed=False, loops=False)

        # check the 1 probability of the output binary matrix
        # should be near to the input P matrix
        self.assertTrue(
            np.isclose(self.p, g2.sum() / (self.n * (self.n - 1)), atol=0.05)
        )

        # check rho
        add = g1 + g2
        add[add != 2] = 0
        output_prob = add.sum() / (2 * self.n * (self.n - 1))
        output_r = np.abs(output_prob - self.p ** 2) / (self.p - self.p ** 2)
        self.assertTrue(np.isclose(self.r, output_r, atol=0.06))

        # check the similarity of g1 and g2
        judge = g1 == g2
        judge.astype(int)
        output_sim = (np.sum(judge) - self.n) / (self.n * (self.n - 1))
        expected_sim = self.p * (self.p + self.r * (1 - self.p)) + (1 - self.p) * (
            1 - self.p * (1 - self.r)
        )
        self.assertTrue(np.isclose(expected_sim, output_sim, atol=0.05))

        # check the dimension of input P and Rho
        self.assertTrue(g1.shape == (self.n, self.n))
        self.assertTrue(g2.shape == (self.n, self.n))


class Test_ER_Corr(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.n = 500
        cls.p = 0.5
        cls.r = 0.3
        cls.P = cls.p * np.ones((cls.n, cls.n))

    def test_bad_input(self):
        with self.assertRaises(TypeError):
            n = "10"
            er_corr(n, self.p, self.r, directed=False, loops=False)

        with self.assertRaises(ValueError):
            n = -1
            er_corr(n, self.p, self.r, directed=False, loops=False)

        with self.assertRaises(TypeError):
            p = "1"
            er_corr(self.n, p, self.r, directed=False, loops=False)

        with self.assertRaises(ValueError):
            p = -0.5
            er_corr(self.n, p, self.r, directed=False, loops=False)

        with self.assertRaises(ValueError):
            p = 5.0
            er_corr(self.n, p, self.r, directed=False, loops=False)

        with self.assertRaises(ValueError):
            r = -0.5
            er_corr(self.n, self.p, r, directed=False, loops=False)

        with self.assertRaises(ValueError):
            r = 5.0
            er_corr(self.n, self.p, r, directed=False, loops=False)

    def test_er_corr(self):
        g1, g2 = er_corr(self.n, self.p, self.r, directed=False, loops=False)
        # check the 1 probability of the output binary matrix
        # should be near to the input P matrix
        self.assertTrue(
            np.isclose(self.p, g2.sum() / (self.n * (self.n - 1)), atol=0.05)
        )

        # check rho
        add = g1 + g2
        add[add != 2] = 0
        output_prob = add.sum() / (2 * self.n * (self.n - 1))
        output_r = np.abs(output_prob - self.p ** 2) / (self.p - self.p ** 2)
        self.assertTrue(np.isclose(self.r, output_r, atol=0.06))

        # check the similarity of g1 and g2
        judge = g1 == g2
        judge.astype(int)
        output_sim = (np.sum(judge) - self.n) / (self.n * (self.n - 1))
        expected_sim = self.p * (self.p + self.r * (1 - self.p)) + (1 - self.p) * (
            1 - self.p * (1 - self.r)
        )
        self.assertTrue(np.isclose(expected_sim, output_sim, atol=0.05))

        # check the dimension of input P and Rho
        self.assertTrue(g1.shape == (self.n, self.n))
        self.assertTrue(g2.shape == (self.n, self.n))


class Test_SBM_Corr(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.n = [100, 100]
        cls.p = [[0.5, 0.2], [0.2, 0.5]]
        cls.r = 0.3
        cls.p1 = np.array(cls.p)

    def test_bad_input(self):
        with self.assertRaises(TypeError):
            n = "1"
            sbm_corr(n, self.p, self.r, directed=False, loops=False)

        with self.assertRaises(ValueError):
            n = ["1", 10]
            sbm_corr(n, self.p, self.r, directed=False, loops=False)

        with self.assertRaises(TypeError):
            p = 0.5
            sbm_corr(self.n, p, self.r, directed=False, loops=False)

        with self.assertRaises(ValueError):
            p = [[0.5]]
            sbm_corr(self.n, p, self.r, directed=False, loops=False)

        with self.assertRaises(ValueError):
            p = [[5, 5], [4, 4]]
            sbm_corr(self.n, p, self.r, directed=False, loops=False)

        with self.assertRaises(ValueError):
            p = ["str"]
            sbm_corr(self.n, p, self.r, directed=False, loops=False)

        with self.assertRaises(ValueError):
            r = -0.5
            sbm_corr(self.n, self.p, r, directed=False, loops=False)

        with self.assertRaises(ValueError):
            r = 5.0
            sbm_corr(self.n, self.p, r, directed=False, loops=False)

        with pytest.raises(TypeError):
            sbm_corr(self.n, self.p, self.r, directed="hey", loops=False)

        with pytest.raises(TypeError):
            sbm_corr(self.n, self.p, self.r, directed=False, loops=6)

    def test_sbm_corr(self):
        g1, g2 = sbm_corr(self.n, self.p, self.r, directed=False, loops=False)
        a1, a2 = g1[0 : self.n[0], 0 : self.n[0]], g1[0 : self.n[0], (self.n[0] + 1) :]
        b1, b2 = g2[0 : self.n[0], 0 : self.n[0]], g2[0 : self.n[0], (self.n[0] + 1) :]
        pb1, pb2 = (
            b1.sum() / (self.n[0] * (self.n[0] - 1)),
            b2.sum() / (self.n[0] * self.n[1]),
        )
        # check the 1 probability of the output binary matrix
        # should be near to the input P matrix
        self.assertTrue(np.isclose(self.p1[0][0], pb1, atol=0.05))
        self.assertTrue(np.isclose(self.p1[0][1], pb2, atol=0.05))

        # check rho
        add1 = a1 + b1
        add1[add1 != 2] = 0
        k1 = (add1.sum() / 2) / (self.n[0] * (self.n[0] - 1))
        l1 = np.abs((k1 - 0.5 ** 2) / (0.5 - 0.5 ** 2))
        add2 = a2 + b2
        add2[add2 != 2] = 0
        k2 = (add2.sum() / 2) / (self.n[0] * self.n[1])
        l2 = np.abs((k2 - 0.2 ** 2) / (0.2 - 0.2 ** 2))
        self.assertTrue(np.isclose(l1, self.r, atol=0.05))
        self.assertTrue(np.isclose(l2, self.r, atol=0.05))

        # check the dimension of input P and Rho
        self.assertTrue(g1.shape == (np.sum(self.n), np.sum(self.n)))
        self.assertTrue(g2.shape == (np.sum(self.n), np.sum(self.n)))
