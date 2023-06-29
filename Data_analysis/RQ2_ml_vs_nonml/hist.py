import pandas as pd
import matplotlib.pyplot as plt

# Load the data into a pandas DataFrame
df = pd.read_csv("data.csv")

# Separate the data into ML and non-ML categories
ml_data = df.loc[df['Category'] == 'ml']
non_ml_data = df.loc[df['Category'] == 'non-ml']

# Plot the histograms
fig, axs = plt.subplots(2, 2, figsize=(12, 8))
axs[0, 0].hist(ml_data['Size of fix'], bins=20)
axs[0, 0].set_title('ML - Size of fix')
axs[0, 0].set_xlabel('Size of fix (lines of code)')
axs[0, 0].set_ylabel('Number of issues')

axs[1, 0].hist(ml_data['Fix duration'], bins=20)
axs[1, 0].set_title('ML - Fix duration')
axs[1, 0].set_xlabel('Fix duration (days)')
axs[1, 0].set_ylabel('Number of issues')

axs[0, 1].hist(non_ml_data['Size of fix'], bins=20)
axs[0, 1].set_title('Non-ML - Size of fix')
axs[0, 1].set_xlabel('Size of fix (lines of code)')
axs[0, 1].set_ylabel('Number of issues')

axs[1, 1].hist(non_ml_data['Fix duration'], bins=20)
axs[1, 1].set_title('Non-ML - Fix duration')
axs[1, 1].set_xlabel('Fix duration (days)')
axs[1, 1].set_ylabel('Number of issues')
plt.figtext(0.5, 0.01, "Distribution of ML and non-ML issues in terms of fix duration and size of fix", ha="center", fontsize=10)

plt.tight_layout()
plt.show()