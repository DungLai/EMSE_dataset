import matplotlib.pyplot as plt

# Categories and number of issues in study A - original taxonomy
categories_a = ['GPU Usage', 'Model', 'Tensor and Input', 'Training Process', 'Third party usage']
issues_a = [11, 74, 185, 85, 20]

# Categories and number of issues in study B - empirical analysis
categories_b = ['GPU Usage', 'Model', 'Tensor and Input', 'Training Process', 'Third party usage']
issues_b = [2, 32, 28, 32, 17]

# Normalise 2 list by dividing each element of the list by the sum of all the elements
total_a = sum(issues_a)
total_b = sum(issues_b)

normalized_a = [value / total_a for value in issues_a]
normalized_b = [value / total_b for value in issues_b]

issues_a = normalized_a
issues_b = normalized_b

# Set up figure and axis
fig, ax = plt.subplots()

# Set x-axis range
x = range(len(categories_a))

# Plot the bar plots for study A and study B
bar_width = 0.35
rects1 = ax.bar(x, issues_a, bar_width, label='Original taxonomy')
rects2 = ax.bar([i + bar_width for i in x], issues_b, bar_width, label='Our empirical analysis')

# Set x-axis tick labels
ax.set_xticks([i + bar_width / 2 for i in x])
ax.set_xticklabels(categories_a)

# Set y-axis label
ax.set_ylabel('Percentage of issues')

# Set title
ax.set_title('Normalised distribution of Machine Learning Categories - Original taxonomy vs. our empirical analysis')

# Add count values on top of the bars
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate('{}'.format(height),
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center', va='bottom')

# Disbale label because we have normalised the data
# autolabel(rects1)
# autolabel(rects2)

# Add legend
ax.legend()

# Show the plot
plt.show()

# chi-square test of independence. This test can determine whether there is a significant association between two categorical variables.
import numpy as np

study_a_observed = np.array(issues_a)
study_b_observed = np.array(issues_b)
from scipy.stats import chisquare

# Combine the observed frequencies from both studies
observed = np.vstack((study_a_observed, study_b_observed))

# Conduct chi-square test
chi2, p_value = chisquare(observed.T)

print("Chi-square statistic:", chi2)
print("P-value:", p_value)
