import pandas as pd
import os

# 假设所有表格都在当前目录下，并且文件名为附件10_仓库处置订单量_Day{day_i}.xlsx
days = [280, 291, 301, 302, 303, 311, 321, 334, 354, 365]
df_total = pd.DataFrame()

# 读取每个表格并合并
for day in days:
    filename = f'附件10_仓库处置订单量_Day{day}.csv'
    df = pd.read_csv(filename, encoding='gbk')
    df = df.rename(columns={"Qty（单位：吨）": f"Day{day}"})
    if df_total.empty:
        df_total = df
    else:
        df_total = pd.merge(df_total, df, on=['Name', 'SKU'], how='outer')

# 将所有NaN值填充为0
df_total.fillna(0, inplace=True)

# 输出结果
df_total.to_csv('总表_仓库处置订单量3.csv', index=False)
