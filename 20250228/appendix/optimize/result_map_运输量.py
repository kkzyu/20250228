import folium
import pandas as pd

# 读取数据
city_info = pd.read_csv('df_loc.csv', encoding='utf-8')  
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

# 标注必开仓库的位置，并根据运输量和SKU类型设置点的颜色和大小
for idx, row in supply_data.iterrows():
    warehouse = row['Name']
    transport_type = row['SKU']  # 运输类型（dm或im）
    qty = row['Qty（单位：吨）']  # 运输量
    
    city_data = city_info[city_info['Location'] == facilities[facilities['Name'] == warehouse]['Location'].values[0]]
    if not city_data.empty:
        city_data = city_data.iloc[0]
        
        # 选择颜色
        color = '#0066FF' if transport_type == 'dm' else '#FF00FF'  # 亮蓝色表示dm，亮紫色表示im

        # 根据运输量设置点的大小
        radius = 5 + (qty / max_qty) * 10  # 基础半径为5，最大增加10

        folium.CircleMarker(
            location=[city_data['Latitude'], city_data['Longitude']],
            radius=radius,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=1,
            popup=f"{warehouse} ({transport_type}) 运输量: {qty} 吨",
        ).add_to(m)

# 添加图例
legend_html = """
     <div style="position: fixed; 
     bottom: 50px; left: 1000px; width: 100px; height: 80px; 
     border:2px solid grey; z-index:9999; font-size:14px;
     background-color:white; opacity: 0.8; padding: 10px;">
     <b>Legend</b><br>
     <i style="background: #0066FF; color:white; padding: 3px;">&nbsp;&nbsp;&nbsp;&nbsp;</i> dm <br>
     <i style="background: #FF00FF; color:white; padding: 3px;">&nbsp;&nbsp;&nbsp;&nbsp;</i> im <br>
     </div>
     """
m.get_root().html.add_child(folium.Element(legend_html))

# 保存地图为HTML文件
m.save("result_map_with_legend.html")
