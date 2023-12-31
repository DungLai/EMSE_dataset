# coding=utf-8
# Copyright (c) 2019 Uber Technologies, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
import logging

import numpy as np
import tensorflow as tf
import tensorflow_addons as tfa
from tensorflow.keras.layers import GRUCell, SimpleRNNCell, LSTMCell
from tensorflow.keras.layers import Layer, Dense, Embedding
from tensorflow.keras.layers import average
from tensorflow_addons.seq2seq import AttentionWrapper
from tensorflow_addons.seq2seq import BahdanauAttention
from tensorflow_addons.seq2seq import LuongAttention

from ludwig.constants import *
from ludwig.modules.reduction_modules import reduce_sequence
from ludwig.utils.misc_utils import get_from_registry
from ludwig.utils.tf_utils import sequence_length_3D, sequence_length_2D

# todo tf2 clean up
# from ludwig.models.modules.attention_modules import \
#     feed_forward_memory_attention
# from ludwig.models.modules.initializer_modules import get_initializer
# from ludwig.models.modules.recurrent_modules import recurrent_decoder

logger = logging.getLogger(__name__)

rnn_layers_registry = {
    'rnn': SimpleRNNCell,
    'gru': GRUCell,
    'lstm': LSTMCell
}


class SequenceGeneratorDecoder(Layer):

    def __init__(
            self,
            num_classes,
            cell_type='rnn',
            state_size=256,
            embedding_size=64,
            beam_width=1,
            num_layers=1,
            attention=None,
            tied_embeddings=None,
            is_timeseries=False,
            max_sequence_length=0,
            use_bias=True,
            weights_initializer='glorot_uniform',
            bias_initializer='zeros',
            weights_regularizer=None,
            bias_regularizer=None,
            activity_regularizer=None,
            reduce_input='sum',
            **kwargs
    ):
        super(SequenceGeneratorDecoder, self).__init__()
        logger.debug(' {}'.format(self.name))

        self.cell_type = cell_type
        self.state_size = state_size
        self.embedding_size = embedding_size
        self.beam_width = beam_width
        self.num_layers = num_layers
        self.attention = attention
        self.attention_mechanism = None
        self.tied_embeddings = tied_embeddings
        self.is_timeseries = is_timeseries
        self.num_classes = num_classes
        self.max_sequence_length = max_sequence_length
        self.state_size = state_size
        self.attention_mechanism = None

        self.reduce_input = reduce_input

        if is_timeseries:
            self.vocab_size = 1
        else:
            self.vocab_size = self.num_classes

        self.GO_SYMBOL = self.vocab_size
        self.END_SYMBOL = 0

        logger.debug('  project input Dense')
        self.project = Dense(
            state_size,
            use_bias=use_bias,
            kernel_initializer=weights_initializer,
            bias_initializer=bias_initializer,
            kernel_regularizer=weights_regularizer,
            bias_regularizer=bias_regularizer,
            activity_regularizer=activity_regularizer
        )

        logger.debug('  Embedding')
        self.decoder_embedding = Embedding(
            input_dim=self.num_classes + 1,  # account for GO_SYMBOL
            output_dim=embedding_size,
            embeddings_initializer=weights_initializer,
            embeddings_regularizer=weights_regularizer,
            activity_regularizer=activity_regularizer
        )
        logger.debug('  project output Dense')
        self.dense_layer = Dense(
            num_classes,
            use_bias=use_bias,
            kernel_initializer=weights_initializer,
            bias_initializer=bias_initializer,
            kernel_regularizer=weights_regularizer,
            bias_regularizer=bias_regularizer,
            activity_regularizer=activity_regularizer
        )
        self.decoder_rnncell = \
            get_from_registry(cell_type, rnn_layers_registry)(state_size)
        logger.debug('  {}'.format(self.decoder_rnncell))

        # Sampler
        self.sampler = tfa.seq2seq.sampler.TrainingSampler()

        logger.debug('setting up attention for', attention)
        if attention is not None:
            if attention == 'luong':
                self.attention_mechanism = LuongAttention(units=state_size)
            elif attention == 'bahdanau':
                self.attention_mechanism = BahdanauAttention(units=state_size)
            logger.debug('  {}'.format(self.attention_mechanism))

            self.decoder_rnncell = AttentionWrapper(
                self.decoder_rnncell,
                self.attention_mechanism,
                attention_layer_size=state_size
            )
            logger.debug('  {}'.format(self.decoder_rnncell))

    def _logits_training(self, inputs, target, training=None):
        input = inputs['hidden']  # shape [batch_size, seq_size, state_size]
        encoder_end_state = self.prepare_encoder_output_state(inputs)

        logits = self.decoder_teacher_forcing(
            input,
            target=target,
            encoder_end_state=encoder_end_state
        )
        return logits  # shape = [b, s, c]

    def prepare_encoder_output_state(self, inputs):

        if 'encoder_output_state' in inputs:
            encoder_output_state = inputs['encoder_output_state']
        else:
            hidden = inputs['hidden']
            if len(hidden.shape) == 3:  # encoder_output is a sequence
                # reduce_sequence returns a [b, h]
                encoder_output_state = reduce_sequence(
                    hidden,
                    self.reduce_input if self.reduce_input else 'sum'
                )
            elif len(hidden.shape) == 2:
                # this returns a [b, h]
                encoder_output_state = hidden
            else:
                raise ValueError("Only works for 1d or 2d encoder_output")

        # now we have to deal with the fact that the state needs to be a list
        # in case of lstm or a tensor otherwise
        if (self.cell_type == 'lstm' and
                isinstance(encoder_output_state, list)):
            if len(encoder_output_state) == 2:
                # this maybe a unidirectionsl lstm or a bidirectional gru / rnn
                # there is no way to tell
                # If it is a unidirectional lstm, pass will work fine
                # if it is bidirectional gru / rnn, the output of one of
                # the directions will be treated as the inital c of the lstm
                # which is weird and may lead to poor performance
                # todo try to find a way to distinguish among these two cases
                pass
            elif len(encoder_output_state) == 4:
                # the encoder was a bidirectional lstm
                # a good strategy is to average the 2 h and the 2 c vectors
                encoder_output_state = [
                    average(
                        [encoder_output_state[0], encoder_output_state[2]]
                    ),
                    average(
                        [encoder_output_state[1], encoder_output_state[3]]
                    )
                ]
            else:
                # no idea how lists of length different than 2 or 4
                # might have been originated, we can either rise an ValueError
                # or deal with it averaging everything
                # raise ValueError(
                #     "encoder_output_state has length different than 2 or 4. "
                #     "Please doublecheck your encoder"
                # )
                average_state = average(encoder_output_state)
                encoder_output_state = [average_state, average_state]

        elif (self.cell_type == 'lstm' and
              not isinstance(encoder_output_state, list)):
            encoder_output_state = [encoder_output_state, encoder_output_state]

        elif (self.cell_type != 'lstm' and
              isinstance(encoder_output_state, list)):
            # here we have a couple options,
            # either reuse part of the input encoder state,
            # or just use its output
            if len(encoder_output_state) == 2:
                # using h and ignoring c
                encoder_output_state = encoder_output_state[0]
            elif len(encoder_output_state) == 4:
                # using average of hs and ignoring cs
                encoder_output_state + average(
                    [encoder_output_state[0], encoder_output_state[2]]
                )
            else:
                # no idea how lists of length different than 2 or 4
                # might have been originated, we can either rise an ValueError
                # or deal with it averaging everything
                # raise ValueError(
                #     "encoder_output_state has length different than 2 or 4. "
                #     "Please doublecheck your encoder"
                # )
                encoder_output_state = average(encoder_output_state)
            # this returns a [b, h]
            # decoder_input_state = reduce_sequence(eo, self.reduce_input)

        elif (self.cell_type != 'lstm' and
              not isinstance(encoder_output_state, list)):
            # do nothing, we are good
            pass

        # at this point decoder_input_state is either a [b,h]
        # or a list([b,h], [b,h]) if the decoder cell is an lstm
        # but h may not be the same as the decoder state size,
        # so we may need to project
        if isinstance(encoder_output_state, list):
            for i in range(len(encoder_output_state)):
                if (encoder_output_state[i].shape[1] !=
                        self.state_size):
                    encoder_output_state[i] = self.project(
                        encoder_output_state[i]
                    )
        else:
            if encoder_output_state.shape[1] != self.state_size:
                encoder_output_state = self.project(
                    encoder_output_state
                )

        return encoder_output_state

    def build_decoder_initial_state(self, batch_size, encoder_state, dtype):
        decoder_initial_state = self.decoder_rnncell.get_initial_state(
            batch_size=batch_size,
            dtype=dtype)

        # handle situation where encoder and decoder are different cell_types
        # and to account for inconsistent wrapping for encoder state w/in lists
        if self.cell_type == 'lstm' and not isinstance(encoder_state, list):
            encoder_state = [encoder_state, encoder_state]
        elif self.cell_type != 'lstm' and isinstance(encoder_state, list):
            encoder_state = encoder_state[0]

        if self.attention_mechanism is not None:
            decoder_initial_state = decoder_initial_state.clone(
                cell_state=encoder_state)
        else:
            if not isinstance(encoder_state, list):
                decoder_initial_state = [encoder_state]
            else:
                decoder_initial_state = encoder_state

        return decoder_initial_state

    def decoder_teacher_forcing(
            self,
            encoder_output,
            target=None,
            encoder_end_state=None
    ):
        # ================ Setup ================
        batch_size = encoder_output.shape[0]

        # Prepare target for decoding
        target_sequence_length = sequence_length_2D(target)
        start_tokens = tf.tile([self.GO_SYMBOL], [batch_size])
        end_tokens = tf.tile([self.END_SYMBOL], [batch_size])
        if self.is_timeseries:
            start_tokens = tf.cast(start_tokens, tf.float32)
            end_tokens = tf.cast(end_tokens, tf.float32)
        targets_with_go_and_eos = tf.concat([
            tf.expand_dims(start_tokens, 1),
            target,  # todo tf2: right now cast to tf.int32, fails if tf.int64
            tf.expand_dims(end_tokens, 1)], 1)
        target_sequence_length_with_eos = target_sequence_length + 1

        # Decoder Embeddings
        decoder_emb_inp = self.decoder_embedding(targets_with_go_and_eos)

        # Setting up decoder memory from encoder output
        if self.attention_mechanism is not None:
            encoder_sequence_length = sequence_length_3D(encoder_output)
            self.attention_mechanism.setup_memory(
                encoder_output,
                memory_sequence_length=encoder_sequence_length
            )

        decoder_initial_state = self.build_decoder_initial_state(
            batch_size,
            encoder_state=encoder_end_state,
            dtype=tf.float32
        )

        decoder = tfa.seq2seq.BasicDecoder(
            self.decoder_rnncell,
            sampler=self.sampler,
            output_layer=self.dense_layer
        )

        # BasicDecoderOutput
        outputs, final_state, generated_sequence_lengths = decoder(
            decoder_emb_inp,
            initial_state=decoder_initial_state,
            sequence_length=target_sequence_length_with_eos
        )

        logits = outputs.rnn_output
        print('\n>>>> logits shape from tfa.seq2seq.BasicDecoder', logits.shape)  #debug
        mask = tf.sequence_mask(
            generated_sequence_lengths,
            maxlen=logits.shape[1],
            dtype=tf.float32
        )
        logits = logits * mask[:, :, tf.newaxis]
        return logits  # , outputs, final_state, generated_sequence_lengths

    def decoder_beam_search(
            self,
            encoder_output,
            encoder_end_state=None,
            training=None
    ):
        # ================ Setup ================
        batch_size = encoder_output.shape[0]
        encoder_sequence_length = sequence_length_3D(encoder_output)

        # ================ predictions =================
        # decoder_input = tf.expand_dims([self.GO_SYMBOL] * batch_size, 1)
        start_tokens = tf.fill([batch_size], self.GO_SYMBOL)
        end_token = self.END_SYMBOL

        # code sequence based on example found here
        # https://www.tensorflow.org/addons/api_docs/python/tfa/seq2seq/BeamSearchDecoder
        tiled_encoder_output = tfa.seq2seq.tile_batch(
            encoder_output,
            multiplier=self.beam_width
        )

        tiled_encoder_end_state = tfa.seq2seq.tile_batch(
            encoder_end_state,
            multiplier=self.beam_width
        )

        tiled_encoder_sequence_length = tfa.seq2seq.tile_batch(
            encoder_sequence_length,
            multiplier=self.beam_width
        )

        if self.attention_mechanism is not None:
            self.attention_mechanism.setup_memory(
                tiled_encoder_output,
                memory_sequence_length=tiled_encoder_sequence_length
            )

        decoder_initial_state = self.build_decoder_initial_state(
            batch_size * self.beam_width,
            encoder_state=tiled_encoder_end_state,
            dtype=tf.float32
        )

        decoder = tfa.seq2seq.beam_search_decoder.BeamSearchDecoder(
            cell=self.decoder_rnncell,
            beam_width=self.beam_width,
            output_layer=self.dense_layer,
            output_all_scores=True,
        )
        # ================ generate logits ==================
        maximum_iterations = self.max_sequence_length

        # initialize inference decoder
        decoder_embedding_matrix = self.decoder_embedding.variables[0]

        # beam search
        decoder_output, decoder_state, decoder_lengths = tfa.seq2seq.dynamic_decode(
            decoder=decoder,
            output_time_major=False,
            impute_finished=False,
            maximum_iterations=maximum_iterations,
            decoder_init_input=decoder_embedding_matrix,
            decoder_init_kwargs=dict(
                start_tokens=start_tokens,
                end_token=end_token,
                # following construct required to work around inconsistent handling
                # of encoder_end_state by tfa
                initial_state=decoder_initial_state \
                    if len(decoder_initial_state) != 1 \
                    else decoder_initial_state[0]
            ),
        )

        predictions = decoder_output.beam_search_decoder_output.predicted_ids[:, :, 0]
        logits = decoder_output.beam_search_decoder_output.scores[:, :, 0, :]
        lengths = decoder_lengths[:, 0]

        last_predictions = tf.gather_nd(
            predictions,
            tf.stack(
                [tf.range(tf.shape(predictions)[0]),
                 tf.maximum(lengths - 1, 0)],
                axis=1
            ),
            name='last_predictions_{}'.format(self.name)
        )

        probabilities = tf.nn.softmax(logits)

        return logits, lengths, predictions, last_predictions, probabilities

    def decoder_greedy(
            self,
            encoder_output,
            encoder_end_state=None,
            training=None
    ):
        # ================ Setup ================
        batch_size = encoder_output.shape[0]

        # ================ predictions =================
        greedy_sampler = tfa.seq2seq.GreedyEmbeddingSampler()

        decoder_input = tf.expand_dims([self.GO_SYMBOL] * batch_size, 1)
        start_tokens = tf.fill([batch_size], self.GO_SYMBOL)
        end_token = self.END_SYMBOL
        decoder_inp_emb = self.decoder_embedding(decoder_input)

        if self.attention_mechanism is not None:
            encoder_sequence_length = sequence_length_3D(encoder_output)
            self.attention_mechanism.setup_memory(
                encoder_output,
                memory_sequence_length=encoder_sequence_length
            )

        decoder_initial_state = self.build_decoder_initial_state(
            batch_size,
            encoder_state=encoder_end_state,
            dtype=tf.float32
        )

        decoder = tfa.seq2seq.BasicDecoder(
            cell=self.decoder_rnncell,
            sampler=greedy_sampler,
            output_layer=self.dense_layer
        )

        # ================ generate logits ==================
        maximum_iterations = self.max_sequence_length

        # initialize inference decoder
        decoder_embedding_matrix = self.decoder_embedding.variables[0]
        decoder_output, decoder_state, decoder_lengths = tfa.seq2seq.dynamic_decode(
            decoder=decoder,
            output_time_major=False,
            impute_finished=False,
            maximum_iterations=maximum_iterations,
            decoder_init_input=decoder_embedding_matrix,
            decoder_init_kwargs=dict(
                start_tokens=start_tokens,
                end_token=end_token,
                initial_state=decoder_initial_state,
            ),
        )

        predictions = decoder_output.sample_id
        logits = decoder_output.rnn_output
        lengths = decoder_lengths

        probabilities = tf.nn.softmax(
            logits,
            name='probabilities_{}'.format(self.name)
        )

        predictions = tf.cast(
            predictions,
            tf.int64,
            name='predictions_{}'.format(self.name)
        )

        last_predictions = tf.gather_nd(
            predictions,
            tf.stack(
                [tf.range(tf.shape(predictions)[0]),
                 tf.maximum(lengths - 1, 0)],
                axis=1
            ),
            name='last_predictions_{}'.format(self.name)
        )

        # mask logits
        mask = tf.sequence_mask(
            lengths,
            maxlen=logits.shape[1],
            dtype=tf.float32
        )

        logits = logits * mask[:, :, tf.newaxis]

        return logits, lengths, predictions, last_predictions, probabilities

    # this should be used only for decoder inference
    def call(self, inputs, training=None, mask=None):
        # shape [batch_size, seq_size, state_size]
        encoder_output = inputs[LOGITS]['hidden']
        # form dependent on cell_type
        # lstm: list([batch_size, state_size], [batch_size, state_size])
        # rnn, gru: [batch_size, state_size]
        encoder_output_state = self.prepare_encoder_output_state(
            inputs[LOGITS]
        )

        if self.beam_width > 1:
            decoder_outputs = self.decoder_beam_search(
                encoder_output,
                encoder_end_state=encoder_output_state,
                training=training
            )
        else:
            decoder_outputs = self.decoder_greedy(
                encoder_output,
                encoder_end_state=encoder_output_state,
                training=training
            )

        logits, lengths, preds, last_preds, probs = decoder_outputs

        return logits, lengths, preds, last_preds, probs

    def _predictions_eval(
            self,
            inputs,  # encoder_output, encoder_output_state
            training=None
    ):
        decoder_outputs = self.call(inputs, training=training)
        logits, lengths, preds, last_preds, probs = decoder_outputs

        return {
            PREDICTIONS: preds,
            LAST_PREDICTIONS: last_preds,
            PROBABILITIES: probs,
            LOGITS: logits
        }


class SequenceTaggerDecoder(Layer):

    def __init__(
            self,
            num_classes,
            use_bias=True,
            weights_initializer='glorot_uniform',
            bias_initializer='zeros',
            weights_regularizer=None,
            bias_regularizer=None,
            activity_regularizer=None,
            attention=False,
            is_timeseries=False,
            **kwargs
    ):
        super(SequenceTaggerDecoder, self).__init__()
        logger.debug(' {}'.format(self.name))

        self.attention = attention

        if is_timeseries:
            num_classes = 1

        logger.debug('  Dense')
        self.projection_layer = Dense(
            units=num_classes,
            use_bias=use_bias,
            kernel_initializer=weights_initializer,
            bias_initializer=bias_initializer,
            kernel_regularizer=weights_regularizer,
            bias_regularizer=bias_regularizer,
            activity_regularizer=activity_regularizer
        )

    def call(
            self,
            inputs,
            training=None,
            mask=None
    ):
        # shape [batch_size, seq_size, state_size]
        if LOGITS in inputs:
            inputs = inputs[LOGITS]
        hidden = inputs['hidden']
        if len(hidden.shape) != 3:
            raise ValueError(
                'Decoder inputs rank is {}, but should be 3 [batch x sequence x hidden] '
                'when using a tagger sequential decoder. '
                'Consider setting reduce_output to null / None if a sequential encoder / combiner is used.'.format(
                    len(hidden.shape)))

        # TODO tf2 add feed forward attention

        # hidden shape [batch_size, sequence_length, hidden_size]
        logits = self.projection_layer(hidden)

        return logits  # logits shape [batch_size, sequence_length, num_classes]

    def _logits_training(
            self,
            inputs,
            training=None,
            mask=None,
            *args,
            **kwarg
    ):
        return self.call(inputs, training=training, mask=mask)

    def _predictions_eval(
            self,
            inputs,  # encoder_output, encoder_output_state
            training=None
    ):
        logits = self.call(inputs, training=training)

        probabilities = tf.nn.softmax(
            logits,
            name='probabilities_{}'.format(self.name)
        )

        predictions = tf.argmax(
            logits,
            -1,
            name='predictions_{}'.format(self.name),
            output_type=tf.int64
        )

        # todo tf2: deal with spurious 0s in predictions
        generated_sequence_lengths = sequence_length_2D(predictions)
        last_predictions = tf.gather_nd(
            predictions,
            tf.stack(
                [tf.range(tf.shape(predictions)[0]),
                 tf.maximum(
                     generated_sequence_lengths - 1,
                     0
                 )],
                axis=1
            ),
            name='last_predictions_{}'.format(self.name)
        )

        # mask logits
        mask = tf.sequence_mask(
            generated_sequence_lengths,
            maxlen=logits.shape[1],
            dtype=tf.float32
        )

        logits = logits * mask[:, :, tf.newaxis]

        return {
            PREDICTIONS: predictions,
            LAST_PREDICTIONS: last_predictions,
            PROBABILITIES: probabilities,
            LOGITS: logits
        }
