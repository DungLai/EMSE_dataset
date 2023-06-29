import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import f_oneway
import seaborn as sns
# Load data into a DataFrame
data = pd.read_csv('data.csv')

# Define the desired order of categories
ml_category_order = ['GPU Usage', 'Model', 'Tensor and Input', 'Training Process', 'Third party usage', 'Other']

# Map numbers to machine learning categories
ml_category_mapping = {
    1: 'GPU Usage',
    2: 'Model',
    3: 'Tensor and Input',
    4: 'Training Process',
    5: 'Third party usage',
    6: 'Other'
}

data['ML category'] = data['ML category'].map(ml_category_mapping)

# Perform descriptive statistics
print(data.describe())

# Create subplots
fig, axs = plt.subplots(2, 1, figsize=(10, 10))

# Create boxplot for fix duration by ML category
sns.boxplot(x='ML category', y='Fix duration (days)', data=data, order=ml_category_order, ax=axs[0])
axs[0].set_title('Boxplot of Fix Duration by ML Category')
axs[0].set_ylabel('Fix Duration (days)')

# Create boxplot for line change by ML category
sns.boxplot(x='ML category', y='Line Change', data=data, order=ml_category_order, ax=axs[1])
axs[1].set_title('Boxplot of Line Change by ML Category')
axs[1].set_ylabel('Line Change')

# Remove automatic suptitle
plt.suptitle('')
plt.tight_layout()
plt.show()

# Group data by ML category
grouped_data = data.groupby('ML category')

# ANOVA test for fix duration
f_val, p_val = f_oneway(*[group['Fix duration (days)'] for name, group in grouped_data])
print("Results of ANOVA test for Fix Duration:")
print("F-value:", f_val)
print("p-value:", p_val)

# ANOVA test for line change
f_val, p_val = f_oneway(*[group['Line Change'] for name, group in grouped_data])
print("\nResults of ANOVA test for Line Change:")
print("F-value:", f_val)
print("p-value:", p_val)

# Create subplots
fig, axs = plt.subplots(len(ml_category_mapping), 2, figsize=(15, 20))

for i, (name, group) in enumerate(grouped_data):
    # Plot histogram for fix duration
    axs[i, 0].hist(group['Fix duration (days)'], bins=30, alpha=0.7)
    axs[i, 0].set_title(f'Fix Duration Histogram for {name}')

    # Plot histogram for line change
    axs[i, 1].hist(group['Line Change'], bins=30, alpha=0.7)
    axs[i, 1].set_title(f'Line Change Histogram for {name}')

plt.tight_layout()
plt.show()

fig, ax = plt.subplots(figsize=(10, 10))

for name, group in grouped_data:
    ax.scatter(group['Fix duration (days)'], group['Line Change'], alpha=0.7, label=name)

ax.set_xlabel('Fix duration (days)')
ax.set_ylabel('Line Change')
ax.set_title('Scatter plot of Fix duration vs Line Change')
ax.legend()
plt.show()

fig, axs = plt.subplots(2, 1, figsize=(10, 10))

# Calculate average fix duration and line change for each ML category
avg_fix_duration = grouped_data['Fix duration (days)'].mean().loc[ml_category_order]
avg_line_change = grouped_data['Line Change'].mean().loc[ml_category_order]

# Plot bar plot for average fix duration
avg_fix_duration.plot(kind='bar', ax=axs[0])
axs[0].set_title('Average Fix Duration by ML Category')
axs[0].set_ylabel('Average Fix Duration (days)')

# Plot bar plot for average line change
avg_line_change.plot(kind='bar', ax=axs[1])
axs[1].set_title('Average Line Change by ML Category')
axs[1].set_ylabel('Average Line Change')

plt.tight_layout()
plt.show()

# each pair

# Calculate mean and median for each ML category
mean_fix_duration = grouped_data['Fix duration (days)'].mean()
median_fix_duration = grouped_data['Fix duration (days)'].median()

mean_line_change = grouped_data['Line Change'].mean()
median_line_change = grouped_data['Line Change'].median()

# Display the mean and median
print("Mean Fix Duration:\n", mean_fix_duration)
print("\nMedian Fix Duration:\n", median_fix_duration)
print("\nMean Line Change:\n", mean_line_change)
print("\nMedian Line Change:\n", median_line_change)

from scipy.stats import mannwhitneyu

# Get the list of ML categories
ml_categories = list(ml_category_mapping.values())

# Loop through each pair of ML categories
for i in range(len(ml_categories)):
    for j in range(i + 1, len(ml_categories)):
        category1 = ml_categories[i]
        category2 = ml_categories[j]

        # Get data for the two categories
        data1 = grouped_data.get_group(category1)
        data2 = grouped_data.get_group(category2)

        # Conduct Mann-Whitney U test for fix duration
        stat, p_value = mannwhitneyu(data1['Fix duration (days)'], data2['Fix duration (days)'])
        print(f'Fix duration: {category1} vs {category2}, p-value: {p_value:.5f}')

        # Conduct Mann-Whitney U test for line change
        stat, p_value = mannwhitneyu(data1['Line Change'], data2['Line Change'])
        print(f'Line Change: {category1} vs {category2}, p-value: {p_value:.5f}\n')
