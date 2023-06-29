import pandas as pd
from scipy.stats import kruskal

# Load data
data = pd.read_csv('data-tidy.csv')

# Prepare data
data_grouped = data.groupby('ML category')

# Extract fix duration data for each ML category
fix_durations = [group['Fix duration (days)'].values for _, group in data_grouped]

# Extract size of fix data for each ML category
sizes_of_fix = [group['Line Change'].values for _, group in data_grouped]

# Perform Kruskal-Wallis test
statistic_duration, p_value_duration = kruskal(*fix_durations)
statistic_size, p_value_size = kruskal(*sizes_of_fix)

print(f"Fix Duration: Kruskal-Wallis H-test test statistic: {statistic_duration}, p-value: {p_value_duration}")
print(f"Size of Fix: Kruskal-Wallis H-test test statistic: {statistic_size}, p-value: {p_value_size}")
