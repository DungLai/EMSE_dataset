# import pandas as pd
# import matplotlib.pyplot as plt

# # read the data into a pandas dataframe
# data = pd.read_csv('data_codechurnsplus.csv')

# # filter the data by category (ml or non-ml)
# ml_data = data[data['Category'] == 'ml']
# non_ml_data = data[data['Category'] == 'non-ml']

# # create a figure with two subplots
# fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(12, 6))

# # create a boxplot for fix duration in each category
# ax1.boxplot([ml_data['Fix duration'], non_ml_data['Fix duration']])
# ax1.set_xticklabels(['ML', 'Non-ML'])
# ax1.set_ylabel('Fix duration (days)')

# # create a boxplot for size of fix in each category
# ax2.boxplot([ml_data['Size of fix'], non_ml_data['Size of fix']])
# ax2.set_xticklabels(['ML', 'Non-ML'])
# ax2.set_ylabel('Size of fix (lines of code)')

# # set the title of the figure
# fig.suptitle('Comparison of ML and Non-ML issues')

# # show the plot
# plt.show()

import pandas as pd
import matplotlib.pyplot as plt

# Function to calculate number of outliers
def calculate_outliers(series):
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    outliers = series[(series < lower_bound) | (series > upper_bound)]
    return outliers.count()

# read the data into a pandas dataframe
data = pd.read_csv('data_codechurnsplus.csv')

# filter the data by category (ml or non-ml)
ml_data = data[data['Category'] == 'ml']
non_ml_data = data[data['Category'] == 'non-ml']

# create a figure with two subplots
fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(12, 6))

# Calculate the number of outliers for fix duration in each category
num_outliers_ml_fix_duration = calculate_outliers(ml_data['Fix duration'])
num_outliers_non_ml_fix_duration = calculate_outliers(non_ml_data['Fix duration'])

# Calculate the number of outliers for size of fix in each category
num_outliers_ml_size_of_fix = calculate_outliers(ml_data['Size of fix'])
num_outliers_non_ml_size_of_fix = calculate_outliers(non_ml_data['Size of fix'])

# create a boxplot for fix duration in each category
ax1.boxplot([ml_data['Fix duration'], non_ml_data['Fix duration']])
ax1.set_xticklabels(['ML', 'Non-ML'])
ax1.set_ylabel('Fix duration (days)')
ax1.set_title(f'Outliers - ML: {num_outliers_ml_fix_duration}, Non-ML: {num_outliers_non_ml_fix_duration}')

# create a boxplot for size of fix in each category
ax2.boxplot([ml_data['Size of fix'], non_ml_data['Size of fix']])
ax2.set_xticklabels(['ML', 'Non-ML'])
ax2.set_ylabel('Size of fix (lines of code)')
ax2.set_title(f'Outliers - ML: {num_outliers_ml_size_of_fix}, Non-ML: {num_outliers_non_ml_size_of_fix}')

# set the title of the figure
fig.suptitle('Comparison of ML and Non-ML issues')

# show the plot
plt.show()
