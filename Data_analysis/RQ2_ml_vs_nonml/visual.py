import pandas as pd
import matplotlib.pyplot as plt

# Load the data
df = pd.read_csv('data.csv')

# Filter the data by category
ml_df = df[df['Category'] == 'ml']
non_ml_df = df[df['Category'] == 'non-ml']

# Compute mean and median fix duration and size of fix for each category
ml_fix_duration_mean = ml_df['Fix duration'].mean()
ml_fix_duration_median = ml_df['Fix duration'].median()
ml_size_of_fix_mean = ml_df['Size of fix'].mean()
ml_size_of_fix_median = ml_df['Size of fix'].median()

non_ml_fix_duration_mean = non_ml_df['Fix duration'].mean()
non_ml_fix_duration_median = non_ml_df['Fix duration'].median()
non_ml_size_of_fix_mean = non_ml_df['Size of fix'].mean()
non_ml_size_of_fix_median = non_ml_df['Size of fix'].median()

# Create bar charts of the mean and median statistics for each category
fix_duration_means = [ml_fix_duration_mean, non_ml_fix_duration_mean]
fix_duration_medians = [ml_fix_duration_median, non_ml_fix_duration_median]
size_of_fix_means = [ml_size_of_fix_mean, non_ml_size_of_fix_mean]
size_of_fix_medians = [ml_size_of_fix_median, non_ml_size_of_fix_median]

fig, axs = plt.subplots(2, 2, figsize=(10, 10))

axs[0, 0].bar(['ML', 'Non-ML'], fix_duration_means)
axs[0, 0].set_title('Mean Fix Duration')
axs[0, 1].bar(['ML', 'Non-ML'], fix_duration_medians)
axs[0, 1].set_title('Median Fix Duration')
axs[1, 0].bar(['ML', 'Non-ML'], size_of_fix_means)
axs[1, 0].set_title('Mean Size of Fix')
axs[1, 1].bar(['ML', 'Non-ML'], size_of_fix_medians)
axs[1, 1].set_title('Median Size of Fix')

plt.show()