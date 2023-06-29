# -*- coding: utf-8 -*-
"""Tests for DOBIN (Distance based Outlier BasIs using Neighbors)."""

__author__ = ["KatieBuc"]

import numpy as np

X = np.array(
    [
        [14.374, 0.075, -0.689, -1.805, 0.370, -0.636],
        [15.184, -1.989, -0.707, 1.466, 0.267, -0.462],
        [14.164, 0.620, 0.365, 0.153, -0.543, 1.432],
        [16.595, -0.056, 0.769, 2.173, 1.208, -0.651],
        [15.330, -0.156, -0.112, 0.476, 1.160, -0.207],
        [14.180, -1.471, 0.881, -0.710, 0.700, -0.393],
        [15.487, -0.478, 0.398, 0.611, 1.587, -0.320],
        [15.738, 0.418, -0.612, -0.934, 0.558, -0.279],
        [15.576, 1.359, 0.341, -1.254, -1.277, 0.494],
        [14.695, -0.103, -1.129, 0.291, -0.573, -0.177],
        [0.302, 0.388, 1.433, -0.443, -1.225, -0.506],
        [0.078, -0.054, 1.980, 0.001, -0.473, 1.343],
        [-15.621, -1.377, -0.367, 0.074, -0.620, -0.215],
        [-17.215, -0.415, -1.044, -0.590, 0.042, -0.180],
        [-13.875, -0.394, 0.570, -0.569, -0.911, -0.100],
        [-15.045, -0.059, -0.135, -0.135, 0.158, 0.713],
        [-15.016, 1.100, 2.402, 1.178, -0.655, -0.074],
        [-14.056, 0.763, -0.039, -1.524, 1.767, -0.038],
        [-14.179, -0.165, 0.690, 0.594, 0.717, -0.682],
        [-14.406, -0.253, 0.028, 0.333, 0.910, -0.324],
        [-14.081, 0.697, -0.743, 1.063, 0.384, 0.060],
        [-14.218, 0.557, 0.189, -0.304, 1.682, -0.589],
    ]
)


# new coords
Y_expected = np.array(
    [
        [0.70483267, -0.5816322, 0.11871428, 0.34552108, -0.09910254, -0.76377905],
        [0.75598487, -0.3995273, 0.77315224, 0.44127426, -0.57290326, -0.15798631],
        [1.39809346, -0.22739085, -0.00691087, 0.95976299, 0.02976105, -0.14004574],
        [1.28905629, -0.13633925, 0.68369824, 0.42504918, -0.71429055, -0.67108882],
        [1.03959645, -0.30184133, 0.54238311, 0.56120644, -0.31085749, -0.67220808],
        [1.01160787, -0.41870196, 0.57815941, 0.09295856, -0.07118286, -0.42409818],
        [1.12021801, -0.26005664, 0.70957693, 0.43559111, -0.29484726, -0.71200991],
        [0.88029154, -0.48277862, 0.17959014, 0.55378539, -0.16981412, -0.74845163],
        [1.23195092, -0.45041353, -0.43099064, 0.62727426, -0.06502084, -0.37224069],
        [0.7829248, -0.45645, 0.12841989, 0.6655479, -0.45474935, -0.32971279],
        [1.08578146, -0.01800754, -0.24099512, 0.04146881, -0.3039681, -0.30324994],
        [1.48556002, 0.18778632, 0.05804308, 0.52291603, 0.21299198, -0.00437453],
        [0.43514895, 0.27618796, 0.20320291, 0.2480942, -0.17456449, -0.04190551],
        [0.33146677, 0.29603738, 0.10524435, 0.43712153, -0.05132798, -0.39590923],
        [0.71628228, 0.27462297, -0.09483719, 0.17156286, -0.06791329, -0.15334237],
        [0.75112256, 0.41796833, 0.11783, 0.63713402, 0.1198619, -0.27663729],
        [1.34017172, 0.67683558, -0.17428047, 0.15828576, -0.35301384, -0.32873135],
        [0.68278866, 0.35335046, 0.20063576, 0.43622768, 0.27183728, -0.99094384],
        [0.7683249, 0.46214507, 0.32043815, 0.14683553, -0.30481544, -0.58480058],
        [0.65894632, 0.42632203, 0.35897602, 0.34393226, -0.16654671, -0.57096877],
        [0.67726471, 0.47746418, 0.13025286, 0.72260868, -0.32161648, -0.52506194],
        [0.70015571, 0.43936681, 0.32210838, 0.29974983, -0.08728308, -0.96448606],
    ]
)


# rotation vector
theta_expected = np.array(
    [
        [0.42165006, -0.86068265, 0.15102382, 0.14601341, -0.18165909, -0.06563891],
        [0.29467119, 0.16927356, -0.63128634, 0.33722485, -0.15896088, -0.58907024],
        [0.75280319, 0.23218556, -0.00239167, -0.59549543, 0.14261205, 0.06647174],
        [0.2451043, 0.36938044, 0.34480381, 0.3022277, -0.73490703, 0.23056968],
        [0.05236588, 0.16004401, 0.67794758, 0.11374533, 0.25620652, -0.65836998],
        [0.32534469, 0.1208541, 0.01269093, 0.63723237, 0.56183902, 0.39705903],
    ]
)