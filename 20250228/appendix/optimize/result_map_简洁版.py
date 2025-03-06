import folium
import pandas as pd
from folium.plugins import FloatImage

# 读取数据
city_info = pd.read_csv('df_loc.csv', encoding='utf-8')  
fruit_stores = pd.read_csv('df_customer.csv', encoding='utf-8')  
facilities = pd.read_csv('df_wh.csv', encoding='utf-8')  
city_names = pd.read_csv('df_list.csv', encoding='gbk')  
supply_data = pd.read_csv('附件11_仓网供应关系1.csv', encoding='gbk')

# 合并城市信息和拼音名称
city_info = pd.merge(city_info, city_names, on="Location", how="left")

# 必开仓库列表
required_facilities = [
    'nei-lu-CDC', 'nan-jing-DC', 'gang-kou-CDC', 'shen-zhen-DC', 
    'tian-jin-DC', 'zheng-zhou-DC', 'ning-bo-DC', 'chong-qing-DC'
]

# 过滤只保留必开的仓库
facilities = facilities[facilities['Name'].isin(required_facilities)]
supply_data = supply_data[supply_data['Name'].isin(required_facilities)]

# 创建浅色主题地图
m = folium.Map(
    location=[35, 110], 
    zoom_start=5,
    tiles='CartoDB positron',  # 浅色背景
    width='2000px', 
    height='2000px'
)

# 获取最大运输量以控制点的大小
max_qty = supply_data['Qty（单位：吨）'].max()

# 添加仓库到门店的运输关系线，并通过透明度表示运输量
for idx, row in supply_data.iterrows():
    warehouse = row['Name']
    customer = row['Customer']
    transport_type = row['SKU']  # 运输类型（dm或im）
    qty = row['Qty（单位：吨）']  # 运输量

    # 计算透明度
    opacity = 0.5 + (qty / max_qty) * 0.5

    # 获取仓库和门店的地理位置
    warehouse_loc = facilities[facilities['Name'] == warehouse]['Location'].values
    customer_loc = fruit_stores[fruit_stores['Name'] == customer]['Location'].values

    if len(warehouse_loc) > 0 and len(customer_loc) > 0:
        warehouse_location = city_info[city_info['Location'] == warehouse_loc[0]]
        customer_location = city_info[city_info['Location'] == customer_loc[0]]

        if not warehouse_location.empty and not customer_location.empty:
            warehouse_latlon = (warehouse_location.iloc[0]['Latitude'], warehouse_location.iloc[0]['Longitude'])
            customer_latlon = (customer_location.iloc[0]['Latitude'], customer_location.iloc[0]['Longitude'])

            # 根据运输类型选择颜色
            line_color = '#0066FF' if transport_type == 'dm' else '#FF00FF'  # 亮蓝色表示dm，亮紫色表示im

            # 使用 PolyLine 添加虚线路径，并根据运输量调整透明度
            folium.PolyLine(
                locations=[warehouse_latlon, customer_latlon],
                weight=2,
                color=line_color,
                opacity=opacity,
                dash_array='5, 20'
            ).add_to(m)

# 标注水果店的位置
store_counts = fruit_stores['Location'].value_counts()
for city, count in store_counts.items():
    city_data_df = city_info[city_info['Location'] == city]
    if not city_data_df.empty:
        city_data = city_data_df.iloc[0]
        folium.CircleMarker(
            location=[city_data['Latitude'], city_data['Longitude']],
            radius=2,
            color='#ff5733',
            fill=True,
            fill_color='#ff5733',
            fill_opacity=1,
            popup=f"{city_data['Location']} 水果店数: {count}",
        ).add_to(m)

# 标注CDC和RDC的位置
for idx, facility in facilities.iterrows():
    city_data = city_info[city_info['Location'] == facility['Location']].iloc[0]
    color = '#3498db' if facility['Type'] == 'CDC' else '#2ecc71'  # CDC 蓝色，RDC 绿色

    folium.CircleMarker(
        location=[city_data['Latitude'], city_data['Longitude']],
        radius=5,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=1,
        popup=f"{facility['Name']} ({facility['Type']})",
    ).add_to(m)

# 添加图例
legend_html = """
     <div style="position: fixed;
     bottom:50px; left: 1000px; width: 150px; height: 120px;
     border:2px solid grey; z-index:9999; font-size:14px;
     background-color:white; opacity: 0.8;
     padding: 10px;">
     <b>Legend</b><br>
     <i style="background: #0066FF; color:white; padding: 2px;"></i>&nbsp;&nbsp; dm  <br>
     <i style="background: #FF00FF; color:white; padding: 2px;"></i>&nbsp;&nbsp; im  <br>
     <i style="background: #3498db; color:white; padding: 2px;"></i>&nbsp;&nbsp; CDC  <br>
     <i style="background: #2ecc71; color:white; padding: 2px;"></i>&nbsp;&nbsp; RDC 
     </div>
     """
m.get_root().html.add_child(folium.Element(legend_html))

# 保存地图为HTML文件
m.save("result_map_with_legend.html")
