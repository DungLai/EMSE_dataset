import pandas as pd

# Load the data
df = pd.read_csv('data_short.csv')

# Split the data into two groups
ml_data = df[df['Category'] == 'ml']['Size of fix']
non_ml_data = df[df['Category'] == 'non-ml']['Size of fix']

# Define a function to calculate descriptive statistics
def calculate_descriptive_stats(series):
    return {
        'Count': series.count(),
        'Mean (lines)': series.mean(),
        'Standard Deviation': series.std(),
        'Minimum (lines)': series.min(),
        '25th Percentile (lines)': series.quantile(0.25),
        'Median (50th Percentile)': series.median(),
        '75th Percentile (lines)': series.quantile(0.75),
        'Maximum (lines)': series.max()
    }

# Calculate the statistics
ml_stats = calculate_descriptive_stats(ml_data)
non_ml_stats = calculate_descriptive_stats(non_ml_data)

# Create a DataFrame for the statistics for easy comparison
stats_df = pd.DataFrame({'ML': ml_stats, 'Non-ML': non_ml_stats})

# Print the result
print(stats_df)

#                                    ML        Non-ML
# Count                      147.000000    147.000000
# Mean (lines)               483.619048    556.809524
# Standard Deviation        1340.406053   2186.084074
# Minimum (lines)              2.000000      1.000000
# 25th Percentile (lines)     22.000000     14.500000
# Median (50th Percentile)    88.000000     80.000000
# 75th Percentile (lines)    341.500000    285.000000
# Maximum (lines)           9126.000000  23767.000000
# [Finished in 10.9s]

# import csv

# # Path to your CSV file
# csv_file_path = 'data_short.csv'

# # Counter for issues with size of fix > 1000
# count_large_fixes = 0

# # Open the CSV file
# with open(csv_file_path, mode='r') as csvfile:
#     # Create a CSV reader object
#     csvreader = csv.DictReader(csvfile)
    
#     # Iterate over each row in the CSV
#     for row in csvreader:
#         # Check if the size of fix is greater than 1000 and the category is 'ml'
#         if int(row['Size of fix']) > 1000 and row['Category'] == 'ml':
#             count_large_fixes += 1

# # Print the result
# print(f"There are {count_large_fixes} ML issues with a size of fix greater than 1000.")