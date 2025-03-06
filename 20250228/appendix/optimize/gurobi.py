import gurobipy as gp
from gurobipy import GRB
import pandas as pd
import csv

# 读取数据
df_customer = pd.read_csv('df_customer.csv')
df_wh = pd.read_csv('df_wh.csv')
df_list = pd.read_csv('df_list.csv', encoding='gbk')
df_loc = pd.read_csv('df_loc.csv')
df_matrix = pd.read_csv('df_matrix.csv')
df_order = pd.read_csv('df_order.csv')
df_proc = pd.read_csv('df_proc.csv')

# 创建拼音到中文城市名称的映射字典
city_name_map = dict(zip(df_list['Location'], df_list['中文名称']))

# 创建模型
model = gp.Model("WarehouseOptimization")

# 定义变量
x = {}  # x[cdc, rdc, sku] 表示从cdc运输到rdc的量
y = {}  # y[wh, store, sku] 表示从仓库（cdc或rdc）运输到门店的量，sku表示水果类型(dm或im)
z = {}  # z[rdc] 表示是否选择开设某个RDC仓库
s = {}  # s[wh] 表示是否为某个仓库购入智能调度系统
t = {}  # t[store, sku] 表示每个门店每种水果类型的时效是否满足

for cdc in df_wh[df_wh['Type'] == 'CDC']['Name']:
    for rdc in df_wh[df_wh['Type'] == 'RDC']['Name']:
        for sku in ['dm', 'im']:
            x[cdc, rdc, sku] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f"x[{cdc},{rdc},{sku}]")
    for store in df_customer['Name']:
        for sku in ['dm', 'im']:
            y[cdc, store, sku] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f"y[{cdc},{store},{sku}]")
            t[store, sku] = model.addVar(vtype=GRB.BINARY, name=f"t[{store},{sku}]")  # 初始化 t 变量
    s[cdc] = model.addVar(vtype=GRB.BINARY, name=f"s[{cdc}]")

for rdc in df_wh[df_wh['Type'] == 'RDC']['Name']:
    z[rdc] = model.addVar(vtype=GRB.BINARY, name=f"z[{rdc}]")
    for store in df_customer['Name']:
        for sku in ['dm', 'im']:
            y[rdc, store, sku] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f"y[{rdc},{store},{sku}]")
            t[store, sku] = model.addVar(vtype=GRB.BINARY, name=f"t[{store},{sku}]")  # 初始化 t 变量
    s[rdc] = model.addVar(vtype=GRB.BINARY, name=f"s[{rdc}]")


# 定义目标函数：最小化总成本
transport_cost = 0
for cdc in df_wh[df_wh['Type'] == 'CDC']['Name']:
    for rdc in df_wh[df_wh['Type'] == 'RDC']['Name']:
        for sku in ['dm', 'im']:
            distance = df_matrix[(df_matrix['From'] == cdc) & (df_matrix['To'] == rdc)]['Distance'].values
            if len(distance) > 0:
                transport_cost += 0.6 * distance[0] * x[cdc, rdc, sku]
    for store in df_customer['Name']:
        for sku in ['dm', 'im']:
            distance = df_matrix[(df_matrix['From'] == cdc) & (df_matrix['To'] == store)]['Distance'].values
            if len(distance) > 0:
                transport_cost += 1.25 * distance[0] * y[cdc, store, sku]

for rdc in df_wh[df_wh['Type'] == 'RDC']['Name']:
    for store in df_customer['Name']:
        for sku in ['dm', 'im']:
            distance = df_matrix[(df_matrix['From'] == rdc) & (df_matrix['To'] == store)]['Distance'].values
            if len(distance) > 0:
                transport_cost += 1.25 * distance[0] * y[rdc, store, sku]

# 将开仓成本单位从万元转换为元
warehouse_cost = sum(z[rdc] * df_proc[df_proc['Name'] == rdc]['Opening_fee'].values[0] * 10000 for rdc in df_wh[df_wh['Type'] == 'RDC']['Name'])

# 加入智能调度系统采购成本（10,000元）
smart_system_cost = sum(s[wh] * 10000 for wh in df_wh['Name'])

# 计算处置成本：考虑智能调度系统的影响，处置成本单位转换为元/吨
processing_cost = 0
for wh in df_wh['Name']:
    original_proc_fee = df_proc[df_proc['Name'] == wh]['Processing_fee'].values[0] * 10000  # 转换为元/吨
    adjusted_proc_fee = original_proc_fee / 2  # 如果购入了智能系统，处置成本折半
    proc_fee = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f"proc_fee[{wh}]")
    model.addConstr(proc_fee == s[wh] * adjusted_proc_fee + (1 - s[wh]) * original_proc_fee)
    for sku in ['dm', 'im']:
        processing_cost += sum(y[wh, store, sku] * proc_fee for store in df_customer['Name'])

# 最终的目标函数
model.setObjective(transport_cost + warehouse_cost + smart_system_cost + processing_cost, GRB.MINIMIZE)

# 定义约束条件

# 1. 每个门店的需求必须得到满足
for store in df_customer['Name']:
    demand_dm = df_order[(df_order['Name'] == store) & (df_order['SKU'] == 'dm')]['qty'].sum()
    demand_im = df_order[(df_order['Name'] == store) & (df_order['SKU'] == 'im')]['qty'].sum()
    model.addConstr(sum(y[wh, store, 'dm'] for wh in df_wh['Name']) == demand_dm)
    model.addConstr(sum(y[wh, store, 'im'] for wh in df_wh['Name']) == demand_im)

# 2. RDC仓库的容量限制和进货出货平衡
for rdc in df_wh[df_wh['Type'] == 'RDC']['Name']:
    capacity = df_proc[df_proc['Name'] == rdc]['Capacity'].values[0]
    # RDC仓库的出货量不能超过其容量
    model.addConstr(sum(y[rdc, store, 'dm'] + y[rdc, store, 'im'] for store in df_customer['Name']) <= capacity * z[rdc])
    # RDC仓库的进货量必须等于出货量（RDC不保留库存）
    for sku in ['dm', 'im']:
        model.addConstr(sum(x[cdc, rdc, sku] for cdc in df_wh[df_wh['Type'] == 'CDC']['Name']) == sum(y[rdc, store, sku] for store in df_customer['Name']))

# 3. CDC仓库只能存储和运输指定类型的水果
for cdc in ['nei-lu-CDC', 'gang-kou-CDC']:
    if cdc == 'nei-lu-CDC':
        # nei-lu-CDC只能处理国产水果
        model.addConstr(sum(y[cdc, store, 'im'] for store in df_customer['Name']) == 0)
    elif cdc == 'gang-kou-CDC':
        # gang-kou-CDC只能处理进口水果
        model.addConstr(sum(y[cdc, store, 'dm'] for store in df_customer['Name']) == 0)

# 4. 一个城市只能开设一个RDC仓库
for location in df_wh[df_wh['Type'] == 'RDC']['Location'].unique():
    model.addConstr(sum(z[rdc] for rdc in df_wh[(df_wh['Type'] == 'RDC') & (df_wh['Location'] == location)]['Name']) <= 1)

# 5. 处置量约束：每个仓库的处置量不能超过其上限
for wh in df_wh['Name']:
    capacity = df_proc[df_proc['Name'] == wh]['Capacity'].values[0]
    if wh in df_wh[df_wh['Type'] == 'RDC']['Name'].values:
        model.addConstr(sum(y[wh, store, 'dm'] + y[wh, store, 'im'] for store in df_customer['Name']) <= capacity * z[wh])
    else:  # CDC仓库
        model.addConstr(sum(y[wh, store, 'dm'] + y[wh, store, 'im'] for store in df_customer['Name']) <= capacity)


# 6. 时效满足率约束
for store in df_customer['Name']:
    for sku in ['dm', 'im']:
        # 查找从CDC或RDC到门店的运输时效
        duration_cdc_to_store = [df_matrix[(df_matrix['From'] == cdc) & (df_matrix['To'] == store)]['Duration'].values[0] for cdc in df_wh[df_wh['Type'] == 'CDC']['Name'] if not df_matrix[(df_matrix['From'] == cdc) & (df_matrix['To'] == store)].empty]
        duration_rdc_to_store = [df_matrix[(df_matrix['From'] == rdc) & (df_matrix['To'] == store)]['Duration'].values[0] for rdc in df_wh[df_wh['Type'] == 'RDC']['Name'] if not df_matrix[(df_matrix['From'] == rdc) & (df_matrix['To'] == store)].empty]

        # 对于每个门店和SKU，检查运输时效是否在10小时以内
        for wh in df_wh['Name']:
            if wh in df_wh[df_wh['Type'] == 'CDC']['Name'].values:
                duration = df_matrix[(df_matrix['From'] == wh) & (df_matrix['To'] == store)]['Duration'].values[0] if not df_matrix[(df_matrix['From'] == wh) & (df_matrix['To'] == store)].empty else None
            else:
                duration = df_matrix[(df_matrix['From'] == wh) & (df_matrix['To'] == store)]['Duration'].values[0] if not df_matrix[(df_matrix['From'] == wh) & (df_matrix['To'] == store)].empty else None

            if duration is not None:
                model.addConstr(t[store, sku] >= (1 - (duration / 683)), name=f"time_constraint[{store},{sku}]") 

# 添加时效满足率约束
total_orders = sum(df_order[df_order['SKU'] == sku]['qty'].sum() for sku in ['dm', 'im'])
total_satisfied_orders = sum(df_order[(df_order['Name'] == store) & (df_order['SKU'] == sku)]['qty'].sum() * t[store, sku] for store in df_customer['Name'] for sku in ['dm', 'im'])

model.addConstr(total_satisfied_orders >= 0.95 * total_orders, name="total_time_satisfaction_rate")

# 优化模型并输出结果
model.optimize()

# 获取选择的RDC仓库
selected_rdc = [rdc for rdc in z if z[rdc].x > 0.5]

# 计算不同SKU的时效满足率
in_time_orders_dm = 0
in_time_orders_im = 0
total_orders_dm = df_order[df_order['SKU'] == 'dm']['qty'].sum()
total_orders_im = df_order[df_order['SKU'] == 'im']['qty'].sum()

for wh in df_wh['Name']:
    for store in df_customer['Name']:
        for sku in ['dm', 'im']:
            # 获取运输量
            qty = y[wh, store, sku].x
            if qty > 0:  # 只输出有运输量的记录
                # 获取运输时效
                duration = df_matrix[(df_matrix['From'] == wh) & (df_matrix['To'] == store)]['Duration'].values
                if len(duration) > 0:
                    duration = duration[0]
                    in_time = duration <= 683  # 检查是否在规定的10小时（600分钟）内
                    if in_time:
                        if sku == 'dm':
                            in_time_orders_dm += qty
                        elif sku == 'im':
                            in_time_orders_im += qty

# 计算国产水果和进口水果的时效满足率
time_satisfaction_rate_dm = in_time_orders_dm / total_orders_dm if total_orders_dm > 0 else 0
time_satisfaction_rate_im = in_time_orders_im / total_orders_im if total_orders_im > 0 else 0

# 构建输出数据
open_warehouse_count = len(selected_rdc) + 2  # 包括必开的两个CDC仓库
total_cost = model.objVal / 10000  # 总物流成本，单位：万元
warehouse_to_warehouse_transport_cost = sum(0.6 * df_matrix[(df_matrix['From'] == cdc) & (df_matrix['To'] == rdc)]['Distance'].values[0] * x[cdc, rdc, sku].x for cdc in df_wh[df_wh['Type'] == 'CDC']['Name'] for rdc in df_wh[df_wh['Type'] == 'RDC']['Name'] for sku in ['dm', 'im']) / 10000  # 仓库之间的运输总成本，单位：万元
warehouse_to_store_transport_cost = sum(1.25 * df_matrix[(df_matrix['From'] == wh) & (df_matrix['To'] == store)]['Distance'].values[0] * y[wh, store, sku].x for wh in df_wh['Name'] for store in df_customer['Name'] for sku in ['dm', 'im']) / 10000  # 仓库到门店的运输总成本，单位：万元
warehouse_opening_cost = sum(z[rdc].x * df_proc[df_proc['Name'] == rdc]['Opening_fee'].values[0] for rdc in df_wh[df_wh['Type'] == 'RDC']['Name'])  # 开仓总成本，单位：万元
processing_cost_total = sum(y[wh, store, sku].x * (s[wh].x * (df_proc[df_proc['Name'] == wh]['Processing_fee'].values[0] * 10000 / 2) + (1 - s[wh].x) * df_proc[df_proc['Name'] == wh]['Processing_fee'].values[0] * 10000) for wh in df_wh['Name'] for store in df_customer['Name'] for sku in ['dm', 'im']) / 10000  # 出入仓处置总成本，单位：万元
smart_system_total_cost = sum(s[wh].x * 10000 for wh in df_wh['Name']) / 10000  # 智能调度系统采购总成本，单位：万元

# 输出文件路径
output_file = '附件9_仓网业务表现1.csv'

# 写入到CSV文件
with open(output_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    # 写入标题
    writer.writerow([
        "开仓数量", 
        "国产水果时效满足率", 
        "进口水果时效满足率", 
        "总物流成本（单位：万元）", 
        "仓库之间的运输总成本（单位：万元）", 
        "仓库到门店的运输总成本（单位：万元）", 
        "开仓总成本（单位：万元）", 
        "出入仓处置总成本（单位：万元）", 
        "智能调度系统采购总成本（单位：万元）"
    ])
    # 写入数据
    writer.writerow([
        open_warehouse_count,
        round(time_satisfaction_rate_dm, 2),
        round(time_satisfaction_rate_im, 2),
        round(total_cost, 2),
        round(warehouse_to_warehouse_transport_cost, 2),
        round(warehouse_to_store_transport_cost, 2),
        round(warehouse_opening_cost, 2),
        round(processing_cost_total, 2),
        round(smart_system_total_cost, 2)
    ])

print(f"结果已成功存储到 {output_file}")

# 从模型结果中提取每个仓库的总处置量
output_data = []
for wh in df_wh['Name']:
    for sku in ['dm', 'im']:
        # 计算该仓库对该 SKU 类型的总处置量
        total_qty = sum(y[wh, store, sku].x for store in df_customer['Name'])
        if total_qty > 0:  # 只输出有处置量的仓库和SKU
            output_data.append([wh, sku, round(total_qty, 2)])

# 输出文件路径
output_file = '附件10_仓库处置订单量1.csv'

# 写入到CSV文件
with open(output_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    # 写入标题
    writer.writerow(["Name", "SKU", "Qty（单位：吨）"])
    # 写入数据
    writer.writerows(output_data)

print(f"结果已成功存储到 {output_file}")

# 从模型结果中提取每个仓库到客户门店的供应关系数据
output_data = []
for wh in df_wh['Name']:
    for store in df_customer['Name']:
        for sku in ['dm', 'im']:
            # 计算该仓库向该门店配送该 SKU 的总量
            qty = y[wh, store, sku].x
            if qty > 0:  # 只输出有配送量的记录
                output_data.append([wh, store, sku, round(qty, 2)])

# 输出文件路径
output_file = '附件11_仓网供应关系1.csv'

# 写入到CSV文件
with open(output_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    # 写入标题
    writer.writerow(["Name", "Customer", "SKU", "Qty（单位：吨）"])
    # 写入数据
    writer.writerows(output_data)

print(f"结果已成功存储到 {output_file}")
