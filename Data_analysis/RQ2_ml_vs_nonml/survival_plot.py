import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from lifelines import KaplanMeierFitter
from lifelines.statistics import logrank_test

# Loading data
data = pd.read_csv('data.csv')

# Create duration and event columns for the Kaplan-Meier fitter
data["duration"] = data["Fix duration"]
data["event"] = 1

# Create two dataframes: one for Machine Learning issues, and another for non-Machine Learning issues
ml_issues = data[data["Category"] == "ml"]
non_ml_issues = data[data["Category"] == "non-ml"]

# Fit the data to the Kaplan-Meier fitter
kmf_ml = KaplanMeierFitter()
kmf_ml.fit(ml_issues["duration"], event_observed=ml_issues["event"], label="Machine Learning Issues")

kmf_non_ml = KaplanMeierFitter()
kmf_non_ml.fit(non_ml_issues["duration"], event_observed=non_ml_issues["event"], label="Non-Machine Learning Issues")

# Plot the survival function
ax = kmf_ml.plot(ci_show=False)
kmf_non_ml.plot(ax=ax, ci_show=False)
plt.title('Survival function of issue fixing: ML vs Non-ML')
plt.ylabel('Survival Probability')
plt.xlabel('Days')
plt.show()

# Perform logrank test
results = logrank_test(ml_issues["duration"], non_ml_issues["duration"], 
                       event_observed_A=ml_issues["event"], event_observed_B=non_ml_issues["event"])
results.print_summary()

# Size of Fix comparison
plt.figure(figsize=(10, 6))
sns.boxplot(x='Category', y='Size of fix', data=data)
plt.title('Size of fix comparison: ML vs Non-ML')
plt.show()

# Fix Duration comparison
plt.figure(figsize=(10, 6))
sns.boxplot(x='Category', y='Fix duration', data=data)
plt.title('Fix duration comparison: ML vs Non-ML')
plt.show()
