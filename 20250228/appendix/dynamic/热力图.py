import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
days = [280, 291, 301, 302, 303, 311, 321, 334, 354, 365]
# 读取合并后的总表
df_total = pd.read_csv('总表_仓库处置订单量3.csv')

# 将数据转换为适合绘制热力图的格式
df_heatmap = df_total.pivot_table(index=['Name', 'SKU'], values=[f'Day{day}' for day in days], aggfunc='sum')

# 绘制热力图
plt.figure(figsize=(12, 8))
sns.heatmap(df_heatmap, cmap='YlGnBu', annot=False, cbar=True)

plt.title('Thermal map of transportation volume of each warehouse on different days')
plt.xlabel('day')
plt.ylabel('warehouse & SKU')
plt.tight_layout()
plt.show()
