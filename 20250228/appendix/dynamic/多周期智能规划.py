import gurobipy as gp
from gurobipy import GRB
import pandas as pd
import csv

def optimize_day(day_i):
    # 读取基础数据
    df_customer = pd.read_csv('df_customer.csv')
    df_wh = pd.read_csv('df_wh.csv')
    df_list = pd.read_csv('df_list.csv', encoding='gbk')
    df_loc = pd.read_csv('df_loc.csv')
    df_matrix = pd.read_csv('df_matrix.csv')
    df_proc = pd.read_csv('df_proc.csv')
    df_orders_year = pd.read_csv('df_orders_year.csv')

    # 创建拼音到中文城市名称的映射字典
    city_name_map = dict(zip(df_list['Location'], df_list['中文名称']))

    # 提取第 day_i 天的订单数据
    df_order = df_orders_year[['Name', 'SKU', f'Day_{day_i}']].copy()
    df_order.columns = ['Name', 'SKU', 'qty']  # 重命名列为统一格式

    # 创建模型
    model = gp.Model("WarehouseOptimization")

    # 定义变量
    x = {}
    y = {}
    z = {}
    s = {}
    t = {}

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

    warehouse_cost = sum(z[rdc] * df_proc[df_proc['Name'] == rdc]['Opening_fee'].values[0] * 10000 for rdc in df_wh[df_wh['Type'] == 'RDC']['Name'])
    smart_system_cost = sum(s[wh] * 10000 for wh in df_wh['Name'])
    processing_cost = 0

    for wh in df_wh['Name']:
        original_proc_fee = df_proc[df_proc['Name'] == wh]['Processing_fee'].values[0] * 10000
        adjusted_proc_fee = original_proc_fee / 2
        proc_fee = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f"proc_fee[{wh}]")
        model.addConstr(proc_fee == s[wh] * adjusted_proc_fee + (1 - s[wh]) * original_proc_fee)
        for sku in ['dm', 'im']:
            processing_cost += sum(y[wh, store, sku] * proc_fee for store in df_customer['Name'])

    model.setObjective(transport_cost + warehouse_cost + smart_system_cost + processing_cost, GRB.MINIMIZE)

    # 定义约束条件
    for store in df_customer['Name']:
        demand_dm = df_order[(df_order['Name'] == store) & (df_order['SKU'] == 'dm')]['qty'].sum()
        demand_im = df_order[(df_order['Name'] == store) & (df_order['SKU'] == 'im')]['qty'].sum()
        model.addConstr(sum(y[wh, store, 'dm'] for wh in df_wh['Name']) == demand_dm)
        model.addConstr(sum(y[wh, store, 'im'] for wh in df_wh['Name']) == demand_im)

    for rdc in df_wh[df_wh['Type'] == 'RDC']['Name']:
        capacity = df_proc[df_proc['Name'] == rdc]['Capacity'].values[0]
        model.addConstr(sum(y[rdc, store, 'dm'] + y[rdc, store, 'im'] for store in df_customer['Name']) <= capacity * z[rdc])
        for sku in ['dm', 'im']:
            model.addConstr(sum(x[cdc, rdc, sku] for cdc in df_wh[df_wh['Type'] == 'CDC']['Name']) == sum(y[rdc, store, sku] for store in df_customer['Name']))

    for cdc in ['nei-lu-CDC', 'gang-kou-CDC']:
        if cdc == 'nei-lu-CDC':
            model.addConstr(sum(y[cdc, store, 'im'] for store in df_customer['Name']) == 0)
        elif cdc == 'gang-kou-CDC':
            model.addConstr(sum(y[cdc, store, 'dm'] for store in df_customer['Name']) == 0)

    for location in df_wh[df_wh['Type'] == 'RDC']['Location'].unique():
        model.addConstr(sum(z[rdc] for rdc in df_wh[(df_wh['Type'] == 'RDC') & (df_wh['Location'] == location)]['Name']) <= 1)

    for wh in df_wh['Name']:
        capacity = df_proc[df_proc['Name'] == wh]['Capacity'].values[0]
        if wh in df_wh[df_wh['Type'] == 'RDC']['Name'].values:
            model.addConstr(sum(y[wh, store, 'dm'] + y[wh, store, 'im'] for store in df_customer['Name']) <= capacity * z[wh])
        else:
            model.addConstr(sum(y[wh, store, 'dm'] + y[wh, store, 'im'] for store in df_customer['Name']) <= capacity)

    for store in df_customer['Name']:
        for sku in ['dm', 'im']:
            duration_cdc_to_store = [df_matrix[(df_matrix['From'] == cdc) & (df_matrix['To'] == store)]['Duration'].values[0] for cdc in df_wh[df_wh['Type'] == 'CDC']['Name'] if not df_matrix[(df_matrix['From'] == cdc) & (df_matrix['To'] == store)].empty]
            duration_rdc_to_store = [df_matrix[(df_matrix['From'] == rdc) & (df_matrix['To'] == store)]['Duration'].values[0] for rdc in df_wh[df_wh['Type'] == 'RDC']['Name'] if not df_matrix[(df_matrix['From'] == rdc) & (df_matrix['To'] == store)].empty]

            for wh in df_wh['Name']:
                if wh in df_wh[df_wh['Type'] == 'CDC']['Name'].values:
                    duration = df_matrix[(df_matrix['From'] == wh) & (df_matrix['To'] == store)]['Duration'].values[0] if not df_matrix[(df_matrix['From'] == wh) & (df_matrix['To'] == store)].empty else None
                else:
                    duration = df_matrix[(df_matrix['From'] == wh) & (df_matrix['To'] == store)]['Duration'].values[0] if not df_matrix[(df_matrix['From'] == wh) & (df_matrix['To'] == store)].empty else None

                if duration is not None:
                    model.addConstr(t[store, sku] >= (1 - (duration / 683)), name=f"time_constraint[{store},{sku}]") 

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
                qty = y[wh, store, sku].x
                if qty > 0:
                    duration = df_matrix[(df_matrix['From'] == wh) & (df_matrix['To'] == store)]['Duration'].values
                    if len(duration) > 0:
                        duration = duration[0]
                        in_time = duration <= 683
                        if in_time:
                            if sku == 'dm':
                                in_time_orders_dm += qty
                            elif sku == 'im':
                                in_time_orders_im += qty

    time_satisfaction_rate_dm = in_time_orders_dm / total_orders_dm if total_orders_dm > 0 else 0
    time_satisfaction_rate_im = in_time_orders_im / total_orders_im if total_orders_im > 0 else 0

    open_warehouse_count = len(selected_rdc) + 2  # 包括必开的两个CDC仓库
    total_cost = model.objVal / 10000  # 总物流成本，单位：万元
    warehouse_to_warehouse_transport_cost = sum(0.6 * df_matrix[(df_matrix['From'] == cdc) & (df_matrix['To'] == rdc)]['Distance'].values[0] * x[cdc, rdc, sku].x for cdc in df_wh[df_wh['Type'] == 'CDC']['Name'] for rdc in df_wh[df_wh['Type'] == 'RDC']['Name'] for sku in ['dm', 'im']) / 10000  # 仓库之间的运输总成本，单位：万元
    warehouse_to_store_transport_cost = sum(1.25 * df_matrix[(df_matrix['From'] == wh) & (df_matrix['To'] == store)]['Distance'].values[0] * y[wh, store, sku].x for wh in df_wh['Name'] for store in df_customer['Name'] for sku in ['dm', 'im']) / 10000  # 仓库到门店的运输总成本，单位：万元
    warehouse_opening_cost = sum(z[rdc].x * df_proc[df_proc['Name'] == rdc]['Opening_fee'].values[0] for rdc in df_wh[df_wh['Type'] == 'RDC']['Name'])  # 开仓总成本，单位：万元
    processing_cost_total = sum(y[wh, store, sku].x * (s[wh].x * (df_proc[df_proc['Name'] == wh]['Processing_fee'].values[0] * 10000 / 2) + (1 - s[wh].x) * df_proc[df_proc['Name'] == wh]['Processing_fee'].values[0] * 10000) for wh in df_wh['Name'] for store in df_customer['Name'] for sku in ['dm', 'im']) / 10000  # 出入仓处置总成本，单位：万元
    smart_system_total_cost = sum(s[wh].x * 10000 for wh in df_wh['Name']) / 10000  # 智能调度系统采购总成本，单位：万元

    # 存储业务表现结果
    output_file = f"附件9_仓网业务表现_Day{day_i}.csv"
    with open(output_file, mode='w', newline='') as file:
        writer = csv.writer(file)
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

    # 存储仓库处置订单量结果
    output_file = f"附件10_仓库处置订单量_Day{day_i}.csv"
    output_data = []
    for wh in df_wh['Name']:
        for sku in ['dm', 'im']:
            total_qty = sum(y[wh, store, sku].x for store in df_customer['Name'])
            if total_qty > 0:
                output_data.append([wh, sku, round(total_qty, 2)])

    with open(output_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Name", "SKU", "Qty（单位：吨）"])
        writer.writerows(output_data)
    print(f"结果已成功存储到 {output_file}")

    # 存储仓网供应关系结果
    output_file = f"附件11_仓网供应关系_Day{day_i}.csv"
    output_data = []
    for wh in df_wh['Name']:
        for store in df_customer['Name']:
            for sku in ['dm', 'im']:
                qty = y[wh, store, sku].x
                if qty > 0:
                    output_data.append([wh, store, sku, round(qty, 2)])

    with open(output_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Name", "Customer", "SKU", "Qty（单位：吨）"])
        writer.writerows(output_data)
    print(f"结果已成功存储到 {output_file}")

# 调用优化函数并传入指定天数
optimize_day(354)  # 示例：传入第1天的数据进行优化
