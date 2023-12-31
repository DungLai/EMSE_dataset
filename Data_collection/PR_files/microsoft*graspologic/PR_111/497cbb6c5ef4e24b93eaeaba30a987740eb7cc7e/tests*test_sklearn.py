import graspy
import numpy as np

from sklearn.utils.estimator_checks import check_estimator

check_estimator(graspy.embed.AdjacencySpectralEmbed)
check_estimator(graspy.embed.ClassicalMDS)
