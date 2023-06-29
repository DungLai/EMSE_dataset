import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd

# assuming you loaded your data into a DataFrame named df
df = pd.read_csv('data.csv')

# Apply logarithmic transformation to the columns
df['Size of fix'] = np.log1p(df['Size of fix'])
df['Fix duration'] = np.log1p(df['Fix duration'])

# Create a figure and axis to hold the plots
fig, ax = plt.subplots(nrows=2, figsize=(10, 10))

# Plot the data
sns.violinplot(x='Category', y='Size of fix', data=df, ax=ax[0])
sns.violinplot(x='Category', y='Fix duration', data=df, ax=ax[1])

# Set the y-axis to logarithmic scale
ax[0].set_yscale('log')
ax[1].set_yscale('log')

# Set the y-axis labels
ax[0].set_ylabel('Log of Size of fix')
ax[1].set_ylabel('Log of Fix duration')

# Set the title
ax[0].set_title('Distribution of Size of fix by Category')
ax[1].set_title('Distribution of Fix duration by Category')

# Show the plot
plt.tight_layout()
plt.show()
