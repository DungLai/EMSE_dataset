import pandas as pd
import matplotlib.pyplot as plt

# read the data into a pandas dataframe
data = pd.read_csv('data.csv')

# filter the data by category (ml or non-ml)
ml_data = data[data['Category'] == 'ml']
non_ml_data = data[data['Category'] == 'non-ml']

# create a figure with two subplots
fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(12, 6))

# create a boxplot for fix duration in each category
ax1.boxplot([ml_data['Fix duration'], non_ml_data['Fix duration']])
ax1.set_xticklabels(['ML', 'Non-ML'])
ax1.set_ylabel('Fix duration (days)')

# create a boxplot for size of fix in each category
ax2.boxplot([ml_data['Size of fix'], non_ml_data['Size of fix']])
ax2.set_xticklabels(['ML', 'Non-ML'])
ax2.set_ylabel('Size of fix (lines of code)')

# set the title of the figure
fig.suptitle('Comparison of ML and Non-ML issues')

# show the plot
plt.show()
