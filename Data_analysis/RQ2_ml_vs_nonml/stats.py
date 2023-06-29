import pandas as pd
import scipy.stats as stats
import matplotlib.pyplot as plt
import seaborn as sns

data = pd.read_csv('data.csv')

non_ml_duration = data[data['Category'] == 'non-ml']['Fix duration']
ml_duration = data[data['Category'] == 'ml']['Fix duration']
non_ml_size = data[data['Category'] == 'non-ml']['Size of fix']
ml_size = data[data['Category'] == 'ml']['Size of fix']

print('Shapiro-Wilk test for fix duration:')
print('Non-machine learning:', stats.shapiro(non_ml_duration))
print('Machine learning:', stats.shapiro(ml_duration))

print('Shapiro-Wilk test for size of fix:')
print('Non-machine learning:', stats.shapiro(non_ml_size))
print('Machine learning:', stats.shapiro(ml_size))


print('Wilcoxon rank-sum test for fix duration:')
print(stats.ranksums(non_ml_duration, ml_duration))

print('Two-sample t-test with Welch\'s correction for mean values of fix duration:')
print(stats.ttest_ind(non_ml_duration, ml_duration, equal_var=False))

print('Wilcoxon rank-sum test for size of fix:')
print(stats.ranksums(non_ml_size, ml_size))

print('Two-sample t-test with Welch\'s correction for mean values of size of fix:')
print(stats.ttest_ind(non_ml_size, ml_size, equal_var=False))

