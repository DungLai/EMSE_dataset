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

import torch

from qucumber.rbm import BinaryRBM
from .wavefunction import Wavefunction


class PositiveWavefunction(Wavefunction):
    """Class capable of learning Wavefunctions with no phase.

    :param num_visible: The number of visible units, ie. the size of the system being learned.
    :type num_visible: int
    :param num_hidden: The number of hidden units in the internal RBM. Defaults to
                       the number of visible units.
    :type num_hidden: int
    :param gpu: Whether to perform computations on the default gpu.
    :type gpu: bool
    """

    _rbm_am = None
    _device = None

    def __init__(self, num_visible, num_hidden=None, gpu=True):
        self.num_visible = int(num_visible)
        self.num_hidden = int(num_hidden) if num_hidden else self.num_visible

        self.rbm_am = BinaryRBM(self.num_visible, self.num_hidden, gpu=gpu)
        self.device = self.rbm_am.device

    @property
    def networks(self):
        return ["rbm_am"]

    @property
    def rbm_am(self):
        return self._rbm_am

    @rbm_am.setter
    def rbm_am(self, new_val):
        self._rbm_am = new_val

    @property
    def device(self):
        return self._device

    @device.setter
    def device(self, new_val):
        self._device = new_val

    def amplitude(self, v):
        r"""Compute the (unnormalized) amplitude of a given vector/matrix of visible states.

        .. math::

            \text{amplitude}(\bm{\sigma})=|\psi_{\bm{\lambda}}(\bm{\sigma})|=
            e^{-\mathcal{E}_{\bm{\lambda}}(\bm{\sigma})/2}

        :param v: visible states :math:`\bm{\sigma}`
        :type v: torch.Tensor

        :returns: Matrix/vector containing the amplitudes of v
        :rtype: torch.Tensor
        """
        return super().amplitude(v)

    def phase(self, v):
        r"""Compute the phase of a given vector/matrix of visible states.

        In the case of a Positive Wavefunction, the phase is just zero.

        :param v: visible states :math:`\bm{\sigma}`
        :type v: torch.Tensor

        :returns: Matrix/vector containing the phases of v
        :rtype: torch.Tensor
        """
        if v.dim() == 1:
            v = v.unsqueeze(0)
            unsqueezed = True
        else:
            unsqueezed = False

        phase = torch.zeros(v.shape[0])

        if unsqueezed:
            return phase.squeeze_(0)
        else:
            return phase

    def psi(self, v):
        r"""Compute the (unnormalized) wavefunction of a given vector/matrix of visible states.

        .. math::

            \psi_{\bm{\lambda}}(\bm{\sigma})
                = e^{-\mathcal{E}_{\bm{\lambda}}(\bm{\sigma})/2}

        :param v: visible states :math:`\bm{\sigma}`
        :type v: torch.Tensor

        :returns: Complex object containing the value of the wavefunction for
                  each visible state
        :rtype: torch.Tensor
        """
        # vector/tensor of shape (len(v),)
        amplitude = self.amplitude(v)

        # complex vector; shape: (2, len(v))
        psi = torch.zeros((2,) + amplitude.shape).to(
            dtype=torch.double, device=self.device
        )
        psi[0] = amplitude

        # squeeze down to complex scalar if there was only one visible state
        return psi.squeeze()

    def gradient(self, v):
        r"""Compute the gradient of the effective energy for a batch of states.

        :math:`\nabla_{\bm{\lambda}}\mathcal{E}_{\bm{\lambda}}(\bm{\sigma})`

        :param v: visible states :math:`\bm{\sigma}`
        :type v: torch.Tensor

        :returns: A single tensor containing all of the parameter gradients.
        :rtype: torch.Tensor
        """
        return self.rbm_am.effective_energy_gradient(v)

    def compute_batch_gradients(self, k, samples_batch, neg_batch):
        """Compute the gradients of a batch of the training data (`samples_batch`).

        :param k: Number of contrastive divergence steps in training.
        :type k: int
        :param samples_batch: Batch of the input samples.
        :type samples_batch: torch.Tensor
        :param neg_batch: Batch of the input samples for computing the
                          negative phase.
        :type neg_batch: torch.Tensor

        :returns: List containing the gradients of the parameters.
        :rtype: list
        """
        return super().compute_batch_gradients(k, samples_batch, neg_batch)

    def fit(
        self,
        data,
        epochs=100,
        pos_batch_size=100,
        neg_batch_size=None,
        k=1,
        lr=1e-3,
        progbar=False,
        starting_epoch=1,
        time=False,
        callbacks=None,
        optimizer=torch.optim.SGD,
        **kwargs
    ):
        """Train the Wavefunction.

        :param data: The training samples
        :type data: numpy.ndarray
        :param epochs: The number of full training passes through the dataset.
                       Technically, this specifies the index of the *last* training
                       epoch, which is relevant if `starting_epoch` is being set.
        :type epochs: int
        :param pos_batch_size: The size of batches for the positive phase
                               taken from the data.
        :type pos_batch_size: int
        :param neg_batch_size: The size of batches for the negative phase
                               taken from the data. Defaults to `pos_batch_size`.
        :type neg_batch_size: int
        :param k: The number of contrastive divergence steps.
        :type k: int
        :param lr: Learning rate
        :type lr: float
        :param progbar: Whether or not to display a progress bar. If "notebook"
                        is passed, will use a Jupyter notebook compatible
                        progress bar.
        :type progbar: bool or str
        :param starting_epoch: The epoch to start from. Useful if continuing training
                               from a previous state.
        :type starting_epoch: int
        :param callbacks: Callbacks to run while training.
        :type callbacks: list[qucumber.callbacks.Callback]
        :param optimizer: The constructor of a torch optimizer.
        :type optimizer: torch.optim.Optimizer
        :param kwargs: Keyword arguments to pass to the optimizer
        """
        return super().fit(
            data=data,
            epochs=epochs,
            pos_batch_size=pos_batch_size,
            neg_batch_size=neg_batch_size,
            k=k,
            lr=lr,
            progbar=progbar,
            starting_epoch=starting_epoch,
            time=time,
            callbacks=callbacks,
            optimizer=optimizer,
            **kwargs
        )

    def compute_normalization(self, space):
        r"""Compute the normalization constant of the wavefunction.

        .. math::

            Z_{\bm{\lambda}}=\sqrt{\sum_{\bm{\sigma}}|\psi_{\bm{\lambda}}|^2}=
            \sqrt{\sum_{\bm{\sigma}} p_{\bm{\lambda}}(\bm{\sigma})}

        :param space: A rank 2 tensor of the entire visible space.
        :type space: torch.Tensor
        """
        return super().compute_normalization(space)

    @staticmethod
    def autoload(location, gpu=False):
        state_dict = torch.load(location)
        wvfn = PositiveWavefunction(
            num_visible=len(state_dict["rbm_am"]["visible_bias"]),
            num_hidden=len(state_dict["rbm_am"]["hidden_bias"]),
            gpu=gpu,
        )
        wvfn.load(location)
        return wvfn