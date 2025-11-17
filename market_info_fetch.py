import pandas as pd

url = "https://docs.google.com/spreadsheets/d/1meVDXRT2eGBdmc1kRmtWiUd7iP-Ik1sxQHC_O4rz8K8/gviz/tq?tqx=out:csv&gid=1767398927"

df = pd.read_csv(url)
df = df[['Symbol', 'Sector', 'Industry', 'MCap Cr']]
df['MCap Cr'] = df['MCap Cr'].apply(lambda x: float(x.replace(',', '')))
df.columns = [x.strip().lower() for x in df.columns]
df.rename(columns={
    'symbol' : 'trading_symbol',
    'sector': 'sector',
    'industry': 'industry',
    'mcap cr': 'market_cap'
}, inplace=True)
df.to_csv('symbol_info.csv', index=False)