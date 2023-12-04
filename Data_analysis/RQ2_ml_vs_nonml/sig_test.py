import pandas as pd

data = pd.read_csv("data_codechurnsplus.csv")
ml_data = data[data['Category'] == 'ml']
non_ml_data = data[data['Category'] == 'non-ml']
from scipy.stats import mannwhitneyu

stat, p = mannwhitneyu(ml_data['Size of fix'], non_ml_data['Size of fix'])

print('Statistics=%.3f, p=%.3f' % (stat, p))
stat, p = mannwhitneyu(ml_data['Fix duration'], non_ml_data['Fix duration'])

print('Statistics=%.3f, p=%.3f' % (stat, p))
