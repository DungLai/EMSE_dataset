import torch
import torchani
import unittest
import os
import pickle
import itertools
import ase
import ase.io
import math
import traceback
from common_aev_test import _TestAEVBase
from torchani.testing import TestCase


path = os.path.dirname(os.path.realpath(__file__))
const_file = os.path.join(path, '../torchani/resources/ani-1x_8x/rHCNO-5.2R_16-3.5A_a4-8.params')  # noqa: E501
N = 97


class TestAEVConstructor(TestCase):
    # Test that checks that the friendly constructor
    # reproduces the values from ANI1x with the correct parameters
    def testCoverLinearly(self):
        consts = torchani.neurochem.Constants(const_file)
        aev_computer = torchani.AEVComputer(**consts)
        ani1x_values = {'radial_cutoff': 5.2,
                        'angular_cutoff': 3.5,
                        'radial_eta': 16.0,
                        'angular_eta': 8.0,
                        'radial_dist_divisions': 16,
                        'angular_dist_divisions': 4,
                        'zeta': 32.0,
                        'angle_sections': 8,
                        'num_species': 4}
        aev_computer_alt = torchani.AEVComputer.cover_linearly(**ani1x_values)
        constants = aev_computer.constants()
        constants_alt = aev_computer_alt.constants()
        for c, ca in zip(constants, constants_alt):
            self.assertEqual(c, ca)


class TestIsolated(TestCase):
    # Tests that there is no error when atoms are separated
    # a distance greater than the cutoff radius from all other atoms
    # this can throw an IndexError for large distances or lone atoms
    def setUp(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        consts = torchani.neurochem.Constants(const_file)
        self.aev_computer = torchani.AEVComputer(**consts).to(self.device)
        self.species_to_tensor = consts.species_to_tensor
        self.rcr = self.aev_computer.Rcr
        self.rca = self.aev_computer.Rca

    def testCO2(self):
        species = self.species_to_tensor(['O', 'C', 'O']).to(self.device).unsqueeze(0)
        distances = [1.0, self.rca,
                     self.rca + 1e-4, self.rcr,
                     self.rcr + 1e-4, 2 * self.rcr]
        error = ()
        for dist in distances:
            coordinates = torch.tensor(
                [[[-dist, 0., 0.], [0., 0., 0.], [0., 0., dist]]],
                requires_grad=True, device=self.device)
            try:
                _, _ = self.aev_computer((species, coordinates))
            except IndexError:
                error = (traceback.format_exc(), dist)
            if error:
                self.fail(f'\n\n{error[0]}\nFailure at distance: {error[1]}\n'
                          f'Radial r_cut of aev_computer: {self.rcr}\n'
                          f'Angular r_cut of aev_computer: {self.rca}')

    def testH2(self):
        species = self.species_to_tensor(['H', 'H']).to(self.device).unsqueeze(0)
        distances = [1.0, self.rca,
                     self.rca + 1e-4, self.rcr,
                     self.rcr + 1e-4, 2 * self.rcr]
        error = ()
        for dist in distances:
            coordinates = torch.tensor(
                [[[0., 0., 0.], [0., 0., dist]]],
                requires_grad=True, device=self.device)
            try:
                _, _ = self.aev_computer((species, coordinates))
            except IndexError:
                error = (traceback.format_exc(), dist)
            if error:
                self.fail(f'\n\n{error[0]}\nFailure at distance: {error[1]}\n'
                          f'Radial r_cut of aev_computer: {self.rcr}\n'
                          f'Angular r_cut of aev_computer: {self.rca}')

    def testH(self):
        # Tests for failure on a single atom
        species = self.species_to_tensor(['H']).to(self.device).unsqueeze(0)
        error = ()
        coordinates = torch.tensor(
            [[[0., 0., 0.]]],
            requires_grad=True, device=self.device)
        try:
            _, _ = self.aev_computer((species, coordinates))
        except IndexError:
            error = (traceback.format_exc())
        if error:
            self.fail(f'\n\n{error}\nFailure on lone atom\n')


class TestAEV(_TestAEVBase):

    def testIsomers(self):
        for i in range(N):
            datafile = os.path.join(path, 'test_data/ANI1_subset/{}'.format(i))
            with open(datafile, 'rb') as f:
                coordinates, species, expected_radial, expected_angular, _, _ \
                    = pickle.load(f)
                coordinates = torch.from_numpy(coordinates)
                species = torch.from_numpy(species)
                expected_radial = torch.from_numpy(expected_radial)
                expected_angular = torch.from_numpy(expected_angular)
                _, aev = self.aev_computer((species, coordinates))
                self.assertAEVEqual(expected_radial, expected_angular, aev)

    def testNoNan(self):
        # AEV should not output NaN even when coordinates are superimposed
        coordinates = torch.ones(1, 3, 3, dtype=torch.float)
        species = torch.zeros(1, 3, dtype=torch.long)
        _, aev = self.aev_computer((species, coordinates))
        self.assertFalse(torch.isnan(aev).any())

    def testPadding(self):
        species_coordinates = []
        radial_angular = []
        for i in range(N):
            datafile = os.path.join(path, 'test_data/ANI1_subset/{}'.format(i))
            with open(datafile, 'rb') as f:
                coordinates, species, radial, angular, _, _ = pickle.load(f)
                coordinates = torch.from_numpy(coordinates)
                species = torch.from_numpy(species)
                radial = torch.from_numpy(radial)
                angular = torch.from_numpy(angular)
                species_coordinates.append(torchani.utils.broadcast_first_dim(
                    {'species': species, 'coordinates': coordinates}))
                radial_angular.append((radial, angular))
        species_coordinates = torchani.utils.pad_atomic_properties(
            species_coordinates)
        _, aev = self.aev_computer((species_coordinates['species'], species_coordinates['coordinates']))
        start = 0
        for expected_radial, expected_angular in radial_angular:
            conformations = expected_radial.shape[0]
            atoms = expected_radial.shape[1]
            aev_ = aev[start:(start + conformations), 0:atoms]
            start += conformations
            self.assertAEVEqual(expected_radial, expected_angular, aev_)


class TestAEVJIT(TestAEV):
    def setUp(self):
        super().setUp()
        self.aev_computer = torch.jit.script(self.aev_computer)


class TestPBCSeeEachOther(TestCase):
    def setUp(self):
        consts = torchani.neurochem.Constants(const_file)
        self.aev_computer = torchani.AEVComputer(**consts).to(torch.double)

    def testTranslationalInvariancePBC(self):
        coordinates = torch.tensor(
            [[[0, 0, 0],
              [1, 0, 0],
              [0, 1, 0],
              [0, 0, 1],
              [0, 1, 1]]],
            dtype=torch.double, requires_grad=True)
        cell = torch.eye(3, dtype=torch.double) * 2
        species = torch.tensor([[1, 0, 0, 0, 0]], dtype=torch.long)
        pbc = torch.ones(3, dtype=torch.bool)

        _, aev = self.aev_computer((species, coordinates), cell=cell, pbc=pbc)

        for _ in range(100):
            translation = torch.randn(3, dtype=torch.double)
            _, aev2 = self.aev_computer((species, coordinates + translation), cell=cell, pbc=pbc)
            self.assertEqual(aev, aev2)

    def testPBCConnersSeeEachOther(self):
        species = torch.tensor([[0, 0]])
        cell = torch.eye(3, dtype=torch.double) * 10
        pbc = torch.ones(3, dtype=torch.bool)
        allshifts = torchani.aev.compute_shifts(cell, pbc, 1)

        xyz1 = torch.tensor([0.1, 0.1, 0.1])
        xyz2s = [
            torch.tensor([9.9, 0.0, 0.0]),
            torch.tensor([0.0, 9.9, 0.0]),
            torch.tensor([0.0, 0.0, 9.9]),
            torch.tensor([9.9, 9.9, 0.0]),
            torch.tensor([0.0, 9.9, 9.9]),
            torch.tensor([9.9, 0.0, 9.9]),
            torch.tensor([9.9, 9.9, 9.9]),
        ]

        for xyz2 in xyz2s:
            coordinates = torch.stack([xyz1, xyz2]).to(torch.double).unsqueeze(0)
            atom_index12, _ = torchani.aev.neighbor_pairs(species == -1, coordinates, cell, allshifts, 1)
            atom_index1, atom_index2 = atom_index12.unbind(0)
            self.assertEqual(atom_index1.tolist(), [0])
            self.assertEqual(atom_index2.tolist(), [1])

    def testPBCSurfaceSeeEachOther(self):
        cell = torch.eye(3, dtype=torch.double) * 10
        pbc = torch.ones(3, dtype=torch.bool)
        allshifts = torchani.aev.compute_shifts(cell, pbc, 1)
        species = torch.tensor([[0, 0]])

        for i in range(3):
            xyz1 = torch.tensor([5.0, 5.0, 5.0], dtype=torch.double)
            xyz1[i] = 0.1
            xyz2 = xyz1.clone()
            xyz2[i] = 9.9

            coordinates = torch.stack([xyz1, xyz2]).unsqueeze(0)
            atom_index12, _ = torchani.aev.neighbor_pairs(species == -1, coordinates, cell, allshifts, 1)
            atom_index1, atom_index2 = atom_index12.unbind(0)
            self.assertEqual(atom_index1.tolist(), [0])
            self.assertEqual(atom_index2.tolist(), [1])

    def testPBCEdgesSeeEachOther(self):
        cell = torch.eye(3, dtype=torch.double) * 10
        pbc = torch.ones(3, dtype=torch.bool)
        allshifts = torchani.aev.compute_shifts(cell, pbc, 1)
        species = torch.tensor([[0, 0]])

        for i, j in itertools.combinations(range(3), 2):
            xyz1 = torch.tensor([5.0, 5.0, 5.0], dtype=torch.double)
            xyz1[i] = 0.1
            xyz1[j] = 0.1
            for new_i, new_j in [[0.1, 9.9], [9.9, 0.1], [9.9, 9.9]]:
                xyz2 = xyz1.clone()
                xyz2[i] = new_i
                xyz2[j] = new_j

            coordinates = torch.stack([xyz1, xyz2]).unsqueeze(0)
            atom_index12, _ = torchani.aev.neighbor_pairs(species == -1, coordinates, cell, allshifts, 1)
            atom_index1, atom_index2 = atom_index12.unbind(0)
            self.assertEqual(atom_index1.tolist(), [0])
            self.assertEqual(atom_index2.tolist(), [1])

    def testNonRectangularPBCConnersSeeEachOther(self):
        species = torch.tensor([[0, 0]])
        cell = ase.geometry.cellpar_to_cell([10, 10, 10 * math.sqrt(2), 90, 45, 90])
        cell = torch.tensor(ase.geometry.complete_cell(cell), dtype=torch.double)
        pbc = torch.ones(3, dtype=torch.bool)
        allshifts = torchani.aev.compute_shifts(cell, pbc, 1)

        xyz1 = torch.tensor([0.1, 0.1, 0.05], dtype=torch.double)
        xyz2 = torch.tensor([10.0, 0.1, 0.1], dtype=torch.double)

        coordinates = torch.stack([xyz1, xyz2]).unsqueeze(0)
        atom_index12, _ = torchani.aev.neighbor_pairs(species == -1, coordinates, cell, allshifts, 1)
        atom_index1, atom_index2 = atom_index12.unbind(0)
        self.assertEqual(atom_index1.tolist(), [0])
        self.assertEqual(atom_index2.tolist(), [1])


class TestAEVOnBoundary(TestCase):

    def setUp(self):
        self.eps = 1e-9
        cell = ase.geometry.cellpar_to_cell([100, 100, 100 * math.sqrt(2), 90, 45, 90])
        self.cell = torch.tensor(ase.geometry.complete_cell(cell), dtype=torch.double)
        self.inv_cell = torch.inverse(self.cell)
        self.coordinates = torch.tensor([[[0.0, 0.0, 0.0],
                                          [1.0, -0.1, -0.1],
                                          [-0.1, 1.0, -0.1],
                                          [-0.1, -0.1, 1.0],
                                          [-1.0, -1.0, -1.0]]], dtype=torch.double)
        self.species = torch.tensor([[1, 0, 0, 0, 0]])
        self.pbc = torch.ones(3, dtype=torch.bool)
        self.v1, self.v2, self.v3 = self.cell
        self.center_coordinates = self.coordinates + 0.5 * (self.v1 + self.v2 + self.v3)
        consts = torchani.neurochem.Constants(const_file)
        self.aev_computer = torchani.AEVComputer(**consts).to(torch.double)

        _, self.aev = self.aev_computer((self.species, self.center_coordinates), cell=self.cell, pbc=self.pbc)

    def assertInCell(self, coordinates):
        coordinates_cell = coordinates @ self.inv_cell
        self.assertEqual(coordinates, coordinates_cell @ self.cell)
        in_cell = (coordinates_cell >= -self.eps) & (coordinates_cell <= 1 + self.eps)
        self.assertTrue(in_cell.all())

    def assertNotInCell(self, coordinates):
        coordinates_cell = coordinates @ self.inv_cell
        self.assertEqual(coordinates, coordinates_cell @ self.cell)
        in_cell = (coordinates_cell >= -self.eps) & (coordinates_cell <= 1 + self.eps)
        self.assertFalse(in_cell.all())

    def testCornerSurfaceAndEdge(self):
        for i, j, k in itertools.product([0, 0.5, 1], repeat=3):
            if i == 0.5 and j == 0.5 and k == 0.5:
                continue
            coordinates = self.coordinates + i * self.v1 + j * self.v2 + k * self.v3
            self.assertNotInCell(coordinates)
            coordinates = torchani.utils.map2central(self.cell, coordinates, self.pbc)
            self.assertInCell(coordinates)
            _, aev = self.aev_computer((self.species, coordinates), cell=self.cell, pbc=self.pbc)
            self.assertGreater(aev.abs().max().item(), 0)
            self.assertEqual(aev, self.aev)


class TestAEVOnBenzenePBC(TestCase):

    def setUp(self):
        consts = torchani.neurochem.Constants(const_file)
        self.aev_computer = torchani.AEVComputer(**consts)
        filename = os.path.join(path, '../tools/generate-unit-test-expect/others/Benzene.json')
        benzene = ase.io.read(filename)
        self.cell = torch.tensor(benzene.get_cell(complete=True)).float()
        self.pbc = torch.tensor(benzene.get_pbc(), dtype=torch.bool)
        species_to_tensor = torchani.utils.ChemicalSymbolsToInts(['H', 'C', 'N', 'O'])
        self.species = species_to_tensor(benzene.get_chemical_symbols()).unsqueeze(0)
        self.coordinates = torch.tensor(benzene.get_positions()).unsqueeze(0).float()
        _, self.aev = self.aev_computer((self.species, self.coordinates), cell=self.cell, pbc=self.pbc)
        self.natoms = self.aev.shape[1]

    def testRepeat(self):
        c1, c2, c3 = self.cell
        species2 = self.species.repeat(1, 4)
        coordinates2 = torch.cat([
            self.coordinates,
            self.coordinates + c1,
            self.coordinates + 2 * c1,
            self.coordinates + 3 * c1,
        ], dim=1)
        cell2 = torch.stack([4 * c1, c2, c3])
        _, aev2 = self.aev_computer((species2, coordinates2), cell=cell2, pbc=self.pbc)
        for i in range(3):
            aev3 = aev2[:, i * self.natoms: (i + 1) * self.natoms, :]
            self.assertEqual(self.aev, aev3)

    def testManualMirror(self):
        c1, c2, c3 = self.cell
        species2 = self.species.repeat(1, 3 ** 3)
        coordinates2 = torch.cat([
            self.coordinates + i * c1 + j * c2 + k * c3
            for i, j, k in itertools.product([0, -1, 1], repeat=3)
        ], dim=1)
        _, aev2 = self.aev_computer((species2, coordinates2))
        aev2 = aev2[:, :self.natoms, :]
        self.assertEqual(self.aev, aev2)


if __name__ == '__main__':
    unittest.main()
