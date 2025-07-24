import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Load the dataset
df = pd.read_csv('data.csv')

# Clean the data by removing missing values and duplicates
df.dropna(inplace=True)
df.drop_duplicates(inplace=True)

# Explore the data by calculating summary statistics and visualizing the data
print(df.describe())
print(df.info())

# Visualize the data using histograms and scatter plots
sns.set()
sns.histplot(df['column1'])
plt.show()

sns.scatterplot(x='column1', y='column2', data=df)
plt.show()

# Perform a regression analysis to identify the relationship between two variables
X = df[['column1']]
y = df['column2']
from sklearn.linear_model import LinearRegression
lr_model = LinearRegression()
lr_model.fit(X, y)
print(lr_model.coef_)
print(lr_model.intercept_)

# Perform a hypothesis test to determine if the relationship is significant
from scipy.stats import ttest_ind
t_stat, p_val = ttest_ind(X, y)
print(t_stat)
print(p_val)

# Visualize the regression line
sns.set()
sns.scatterplot(x='column1', y='column2', data=df)
plt.plot(X, lr_model.predict(X), 'r-')
plt.show()
