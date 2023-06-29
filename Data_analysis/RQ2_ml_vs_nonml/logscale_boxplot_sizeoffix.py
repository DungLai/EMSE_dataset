import pandas as pd
import matplotlib.pyplot as plt

# Read the data from CSV file
df = pd.read_csv('data.csv')

# Set the figure size
plt.figure(figsize=(8, 6))

# Generate the box plot with logarithmic scale (rotated 90 degrees)
plt.boxplot([df[df['Category'] == 'non-ml']['Size of fix'], df[df['Category'] == 'ml']['Size of fix']], vert=True, sym='b.')
plt.yscale('log')

# Set labels and title
plt.xlabel('Category')
plt.ylabel('Size of Fix (Log Scale)')
plt.title('Comparison of Size of Fix using Log Scale: Machine Learning vs. Non-Machine Learning')

# Set x-axis tick labels
plt.xticks([1, 2], ['Non-ML', 'ML'])

# Display the plot
plt.show()

import csv

category = 'ml'
size_threshold = 1000
count = 0

with open('data.csv', 'r') as file:
    reader = csv.DictReader(file)
    for row in reader:
        if row['Category'] == category and int(row['Size of fix']) > size_threshold:
            count += 1

print("Number of rows satisfying the criteria:", count)
