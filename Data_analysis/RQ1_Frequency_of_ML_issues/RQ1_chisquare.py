import numpy as np
from scipy.stats import chi2_contingency

# Observed frequencies
our_study = [2, 32, 28, 32, 17]
humbatova_study = [11, 74, 185, 85, 20]

# Create the contingency table
contingency_table = np.array([our_study, humbatova_study])

# Perform the chi-square test
chi2, p_value, dof, expected = chi2_contingency(contingency_table)

# Print the results
print("Chi-square test statistic:", chi2)
print("Degrees of freedom:", dof)
print("P-value:", p_value)

# Effect size

# Create the contingency table
observed = np.array([[11, 2],
                     [74, 32],
                     [185, 28],
                     [85, 32],
                     [20, 17]])

# Calculate the effect size (Cramer's V)
n = np.sum(observed)  # Total sample size
r, c = observed.shape  # Number of rows and columns in the contingency table

V = np.sqrt(chi2 / (n * min(r, c) - 1))

# Print the effect size (Cramer's V)
print("Effect size (Cramer's V):", V)