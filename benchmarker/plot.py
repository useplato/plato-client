import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# TODO: haven't tested this yet

# Read the CSV file
df = pd.read_csv('ood_req.csv')

# Set the style for better visualization
plt.style.use('seaborn')

# Create the plot
plt.figure(figsize=(10, 6))
sns.scatterplot(data=df, x='total_runs_for_csv', y='ood_requests_overall')

# Customize the plot
plt.title('OOD Requests vs Total Runs', fontsize=14)
plt.xlabel('Total Runs', fontsize=12)
plt.ylabel('OOD Requests', fontsize=12)

# Add a trend line
sns.regplot(data=df, x='total_runs_for_csv', y='ood_requests_overall', scatter=False, color='red')

# Adjust layout
plt.tight_layout()

# Save the plot
plt.savefig('ood_requests_plot.png')
plt.close()
