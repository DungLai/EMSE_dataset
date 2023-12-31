import os

os.environ["MKL_NUM_THREADS"] = "1"  # must be done before numpy import!!
os.environ["NUMEXPR_NUM_THREADS"] = "1"  # must be done before numpy import!!
os.environ["OMP_NUM_THREADS"] = "1"  # must be done before numpy import!!

import numpy as np
from sklearn.preprocessing import FunctionTransformer
from sklearn.tree import DecisionTreeClassifier
from statsmodels.tsa.stattools import acf

from sktime.transformers.compose import RowwiseTransformer
from sktime.transformers.segment import RandomIntervalSegmenter
from sktime.transformers.compose import Tabulariser
from sktime.series_as_features.compose.pipeline import Pipeline
from sktime.series_as_features.compose.pipeline import FeatureUnion
from sktime.series_as_features.compose import TimeSeriesForestClassifier
from sktime.utils.time_series import time_series_slope
import sktime.classification.interval_based.tsf as ib
import sktime.classification.frequency_based.rise as fb
import sktime.classification.dictionary_based.boss as db
import sktime.classification.distance_based.time_series_neighbors as dist
import sktime.contrib.experiments as exp

#method 1



benchmark_datasets = [
    "ACSF1",
    "Adiac",
    "ArrowHead",
    "Beef",
    "BeetleFly",
    "BirdChicken",
    "BME",
    "Car",
    "CBF",
    "ChlorineConcentration",
    "CinCECGTorso",
    "Coffee",
    "Computers",
    "CricketX",
    "CricketY",
    "CricketZ",
    "DiatomSizeReduction",
    "DistalPhalanxOutlineCorrect",
    "DistalPhalanxOutlineAgeGroup",
    "DistalPhalanxTW",
    "Earthquakes",
    "ECG200",
    "ECG5000",
    "ECGFiveDays",
    "EOGHorizontalSignal",
    "EOGVerticalSignal",
    "EthanolLevel",
    "FaceAll",
    "FaceFour",
    "FacesUCR",
    "FiftyWords",
    "Fish",
    "FreezerRegularTrain",
    "FreezerSmallTrain",
    "Ham",
    "Haptics",
    "Herring",
    "InlineSkate",
    "InsectEPGRegularTrain",
    "InsectEPGSmallTrain",
    "InsectWingbeatSound",
    "ItalyPowerDemand",
    "LargeKitchenAppliances",
    "Lightning2",
    "Lightning7",
    "Mallat",
    "Meat",
    "MedicalImages",
    "MiddlePhalanxOutlineCorrect",
    "MiddlePhalanxOutlineAgeGroup",
    "MiddlePhalanxTW",
    "MixedShapesRegularTrain",
    "MixedShapesSmallTrain",
    "MoteStrain",
    "OliveOil",
    "OSULeaf",
    "PhalangesOutlinesCorrect",
    "Phoneme",
    "PigAirwayPressure",
    "PigArtPressure",
    "PigCVP",
    "Plane",
    "PowerCons",
    "ProximalPhalanxOutlineCorrect",
    "ProximalPhalanxOutlineAgeGroup",
    "ProximalPhalanxTW",
    "RefrigerationDevices",
    "Rock",
    "ScreenType",
    "SemgHandGenderCh2",
    "SemgHandMovementCh2",
    "SemgHandSubjectCh2",
    "ShapeletSim",
    "SmallKitchenAppliances",
    "SmoothSubspace",
    "SonyAIBORobotSurface1",
    "SonyAIBORobotSurface2",
    "Strawberry",
    "SwedishLeaf",
    "Symbols",
    "SyntheticControl",
    "ToeSegmentation1",
    "ToeSegmentation2",
    "Trace",
    "TwoLeadECG",
    "TwoPatterns",
    "UMD",
    "UWaveGestureLibraryX",
    "UWaveGestureLibraryY",
    "UWaveGestureLibraryZ",
    "Wafer",
    "Wine",
    "WordSynonyms",
    "Worms",
    "WormsTwoClass",
    "Yoga"
]

data_dir = "Z:/ArchiveData/Univariate_ts/"
results_dir="Z:/Benchmarking/"

def acf_coefs(x, maxlag=100):
    x = np.asarray(x).ravel()
    nlags = np.minimum(len(x) - 1, maxlag)
    return acf(x, nlags=nlags).ravel()

def powerspectrum(x, **kwargs):
    x = np.asarray(x).ravel()
    fft = np.fft.fft(x)
    ps = fft.real * fft.real + fft.imag * fft.imag
    return ps[:ps.shape[0] // 2].ravel()


def tsf_benchmarking():
    for i in range(0, len(benchmark_datasets)):
        dataset = benchmark_datasets[i]
        print(str(i)+" problem = "+dataset)
        tsf = ib.TimeSeriesForest(n_trees=100)
        exp.run_experiment(overwrite=False, problem_path=data_dir, results_path=results_dir, cls_name="PythonTSF",
                           classifier=tsf,dataset=dataset, train_file=False)
        steps = [
            ('segment', RandomIntervalSegmenter(n_intervals='sqrt')),
            ('transform', FeatureUnion([
                ('mean', RowwiseTransformer(FunctionTransformer(func=np.mean, validate=False))),
                ('std', RowwiseTransformer(FunctionTransformer(func=np.std, validate=False))),
                ('slope', RowwiseTransformer(FunctionTransformer(func=time_series_slope, validate=False)))
            ])),
            ('clf', DecisionTreeClassifier())
        ]
        base_estimator = Pipeline(steps)
        tsf = TimeSeriesForestClassifier(base_estimator=base_estimator,
                                         n_estimators=100)
        exp.run_experiment(overwrite=False, problem_path=data_dir, results_path=results_dir, cls_name="PythonTSFComposite",
                       classifier=tsf, dataset=dataset, train_file=False)

def rise_benchmarking():
    for i in range(0, len(benchmark_datasets)):
        dataset = benchmark_datasets[i]
        print(str(i)+" problem = "+dataset)
        rise = fb.RandomIntervalSpectralForest(n_trees=100)
        exp.run_experiment(overwrite=True, problem_path=data_dir, results_path=results_dir, cls_name="PythonRISE",
                           classifier=rise,dataset=dataset, train_file=False)
        steps = [
            ('segment', RandomIntervalSegmenter(n_intervals=1, min_length=5)),
            ('transform', FeatureUnion([
                ('acf', RowwiseTransformer(FunctionTransformer(func=acf_coefs, validate=False))),
                ('ps', RowwiseTransformer(FunctionTransformer(func=powerspectrum, validate=False)))
            ])),
            ('tabularise', Tabulariser()),
            ('clf', DecisionTreeClassifier())
        ]
        base_estimator = Pipeline(steps)
        rise = TimeSeriesForestClassifier(base_estimator=base_estimator, n_estimators=100)
        exp.run_experiment(overwrite=True, problem_path=data_dir, results_path=results_dir, cls_name="PythonRISEComposite",
                       classifier=rise, dataset=dataset, train_file=False)

def boss_benchmarking():
    for i in range(0, int(len(benchmark_datasets))):
        dataset = benchmark_datasets[i]
        print(str(i)+" problem = "+dataset+ " writing to "+ results_dir+"/BOSS/")
        boss = db.BOSSEnsemble()
        exp.run_experiment(overwrite=False, problem_path=data_dir, results_path=results_dir+"/BOSS/", cls_name="PythonBOSS",
                           classifier=boss,dataset=dataset, train_file=False)


distance_test = [
    "Chinatown",
    "ItalyPowerDemand",
]




def elastic_distance_benchmarking():
    for i in range(0, int(len(distance_test))):
        dataset = distance_test[i]
        print(str(i)+" problem = "+dataset+ " writing to "+ results_dir+"/DTW/")
        dtw=dist.KNeighborsTimeSeriesClassifier(metric="dtw")
        exp.run_experiment(overwrite=False, problem_path=data_dir, results_path=results_dir+"/DTW/", cls_name="PythonDTW",
                           classifier=dtw,dataset=dataset, train_file=False)
        twe=dist.KNeighborsTimeSeriesClassifier(metric="dtw")
        exp.run_experiment(overwrite=False, problem_path=data_dir, results_path=results_dir+"/DTW/", cls_name="PythonTWE",
                           classifier=twe,dataset=dataset, train_file=False)




if __name__ == "__main__":
#    tsf_benchmarking()
#    rise_benchmarking()
#    boss_benchmarking()
    elastic_distance_benchmarking()