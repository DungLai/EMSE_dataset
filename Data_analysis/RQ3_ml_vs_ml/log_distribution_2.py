import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Define the data
data = pd.read_csv('data-tidy.csv')

# Map the category numbers to their labels
category_labels = {
    1: 'GPU Usage',
    2: 'Model',
    3: 'Tensor and Input',
    4: 'Training Process',
    5: 'Third party usage',
    6: 'Other'
}

# Create a list to store the data for each category
category_data = []
category_order = [1, 2, 3, 4, 5, 6]
for category in category_order:
    category_data.append(data[data['ML category'] == category]['Line Change'])

# Create the box plots
fig, ax = plt.subplots()
ax.boxplot(category_data, labels=[category_labels[i] for i in category_order], showfliers=False)
ax.set_yscale('log')  # Set the y-axis scale to logarithmic

# Set the axis labels and title
ax.set_xlabel('Machine Learning Category')
ax.set_ylabel('Line Change (Log Scale)')
ax.set_title('Distribution of Line Change by Machine Learning Category (Log Scale)')

# Rotate the x-axis labels for better readability
plt.xticks(rotation=45)

# Display the plot
plt.show()
