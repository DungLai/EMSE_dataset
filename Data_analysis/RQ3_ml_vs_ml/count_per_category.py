import matplotlib.pyplot as plt
import pandas as pd

# Define the data
data = pd.read_csv('data.csv')

# Define the desired order of categories
category_order = [1, 2, 3, 4, 5, 6]

# Map the category numbers to their labels
category_labels = {
    1: 'GPU Usage',
    2: 'Model',
    3: 'Tensor and Input',
    4: 'Training Process',
    5: 'Third party usage',
    6: 'Other'
}

# Count the occurrences of each category in the desired order
category_counts = data['ML category'].value_counts().sort_index().loc[category_order]

# Create the bar chart
fig, ax = plt.subplots()
bars = ax.bar([category_labels[category] for category in category_counts.index], category_counts)

# Add the count values on top of the bars
for bar in bars:
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width() / 2, height, height, ha='center', va='bottom')

# Set the axis labels and title
ax.set_xlabel('Machine Learning Category')
ax.set_ylabel('Count')
ax.set_title('Count of Machine Learning Issues by Category')

# Rotate the x-axis labels for better readability
plt.xticks(rotation=45)

# Display the plot
plt.show()
