from tqdm import tqdm

from keras import backend as K

import tensorflow as tf
from keras.models import model_from_json

from ..utils.results import run_round_results, save_result
from ..parameters.round_params import round_params
from ..utils.results import create_header
from ..metrics.entropy import epoch_entropy
from ..model.ingest_model import ingest_model
from ..metrics.score_model import get_score
from ..utils.logging import write_log
from ..utils.results import result_todf, peak_epochs_todf
from ..reducers.reduce_run import reduce_run
from ..utils.exceptions import TalosReturnError


def scan_run(self):

    '''The high-level management of the scan procedures
    onwards from preparation. Manages round_run()'''

    # enforce round_limit
    self.param_grid = self.param_grid[:self.round_limit]

    # main loop for the experiment
    # NOTE: the progress bar is also updated on line 73
    self.pbar = tqdm(total=len(self.param_log),
                     disable=self.disable_progress_bar)
    while len(self.param_log) != 0:
        self = rounds_run(self)
        self.pbar.update(1)
    self.pbar.close()

    # save the results
    self = result_todf(self)
    self.peak_epochs_df = peak_epochs_todf(self)
    self._null = self.logfile.close()

    print('Scan Finished!')


def rounds_run(self):

    '''The main operational function that manages the experiment
    on the level of execution of each round.'''

    # determine the parameters for the particular execution
    self.round_params = round_params(self)

    # print round params
    if self.print_params is True:
        print(self.round_params)

    # compile the model
    try:
        _hr_out, self.keras_model = ingest_model(self)
    except TypeError:
        raise TalosReturnError("Make sure that input model returns 'out, model' where out is history object from model.fit()")

    # create log and other stats
    try:
        self.epoch_entropy.append(epoch_entropy((_hr_out)))
    except (TypeError, AttributeError):
        raise TalosReturnError("Make sure that input model returns in the order 'out, model'")

    if self.round_counter == 0:
        _for_header = create_header(self, _hr_out)
        self.result.append(_for_header)
        save_result(self)

    _hr_out = run_round_results(self, _hr_out)
    self._val_score = get_score(self)
    write_log(self)
    self.result.append(_hr_out)
    save_result(self)

    # apply reduction
    if self.reduction_method is not None:
        if (self.round_counter + 1) % self.reduction_interval == 0:
            len_before_reduce = len(self.param_log)
            self = reduce_run(self)
            total_reduced = len_before_reduce - len(self.param_log)
            # update the progress bar
            self.pbar.update(total_reduced)

    # save model and weights
    self.saved_models.append(self.keras_model.to_json())
    self.saved_weights.append(self.keras_model.get_weights())

    # clear tensorflow sessions (maybe)
    if self.clear_tf_session is True:
        K.clear_session()
    self.round_counter += 1

    return self
