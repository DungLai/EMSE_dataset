import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Load the data
df = pd.read_csv('data.csv')

# Replace the category numbers with their actual names for better visualization
category_order = ['GPU Usage', 'Model', 'Tensor and Input', 'Training Process', 'Third party usage', 'Other']
df['ML category'] = df['ML category'].replace({1: 'GPU Usage', 2: 'Model', 3: 'Tensor and Input', 
                                               4: 'Training Process', 5: 'Third party usage', 6: 'Other'})

# Applying logarithmic transformation to 'Line Change' and 'Fix duration (days)'
df['Line Change'] = np.log1p(df['Line Change'])
df['Fix duration (days)'] = np.log1p(df['Fix duration (days)'])

# Create a subplot to hold two violin plots
fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(16, 8))

# Create the violin plots with the specified order of categories
sns.violinplot(x='ML category', y='Line Change', data=df, order=category_order, ax=axes[0])
sns.violinplot(x='ML category', y='Fix duration (days)', data=df, order=category_order, ax=axes[1])

# Set the titles
axes[0].set_title('Violin plot of Size of Fix (Log Scale)')
axes[1].set_title('Violin plot of Fix Duration (Log Scale)')

# Rotate x-axis labels for better visibility
for ax in axes:
    plt.sca(ax)
    plt.xticks(rotation=45)

# Display the plots
plt.tight_layout()
plt.show()