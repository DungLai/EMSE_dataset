# Copyright 2018 PIQuIL - All Rights Reserved

# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at

#   http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from .observable import Observable
from .utils import to_pm1


class NeighbourInteraction(Observable):
    r"""The :math:`\sigma^z_i \sigma^z_{i+c}` observable

    Computes the :math:`c^\text{th}` nearest neighbour interaction for a spin chain with
    either open or periodic boundary conditions.

    :param periodic_bcs: Specifies whether the system has periodic boundary
                         conditions.
    :type periodic_bcs: bool
    :param c: Interaction distance.
    :type c: int
    """

    def __init__(self, periodic_bcs=False, c=1):
        self.periodic_bcs = periodic_bcs
        self.c = c

        self.name = "NeighbourInteraction(periodic_bcs={}, c={})".format(
            self.periodic_bcs, self.c
        )
        self.symbol = "(Z_i * Z_(i+{}))".format(self.c)

    def apply(self, nn_state, samples):
        r"""Computes the energy of this neighbour interaction for each sample
        given a batch of samples.

        :param nn_state: The Wavefunction that drew the samples.
        :type nn_state: qucumber.nn_states.Wavefunction
        :param samples: A batch of samples to calculate the observable on.
                        Must be using the :math:`\sigma_i = 0, 1` convention.
        :type samples: torch.Tensor
        """

        samples = to_pm1(samples)  # convert to +/- 1 format
        L = samples.shape[-1]  # length of the spin chain
        if self.periodic_bcs:
            perm_indices = [(i + self.c) % L for i in range(L)]
            interaction_terms = samples * samples[:, perm_indices]
        else:
            interaction_terms = samples[:, : -self.c] * samples[:, self.c :]

        # average over spin sites.
        # not using mean bc interaction_terms.shape[-1] < num_spins = L
        return interaction_terms.sum(1).div_(L)
