import pandas as pd

df = pd.read_csv('write_worksheet_title.csv')
x = df[df['sector'].isna()]['trading_symbol'].unique()
print(x)