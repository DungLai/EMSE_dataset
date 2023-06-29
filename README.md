# This folder contains scripts for data analysis and data collections process used in the EMSE journal paper - Comparative analysis of real bugs in open-source machine learning projects

Dataset:

* all_issues.csv: 147 ML issues and 147 non-ML issues being used for the data analysis to answer RQ1 and RQ2.
* Labelled_ML_issues_data.csv: 147 ML issues being manually labelled into 6 categories: (1 - GPU Usage; 2 - Model; 3 - Tensor and Input; 4 - Training Process; 5 - Third party usage; 6 - Other)

Each folder bellow has a dedicated README file for instruction and explanation on how to run the scripts.

* Data_analysis: This folder contains the scripts to run the statistical tests and visualisations to answer each research question.
* Data_collection: This folder contains the ML issues and non-ML issues dataset, scripts and instructions to replicate the data collection pipeline
* Suplementary_material: This folder contains supplementary visualisations, the technical report for applying the revised Humbatova's taxonomy, and the list of ML keywords used in the data collection process.