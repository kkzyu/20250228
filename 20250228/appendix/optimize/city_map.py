import folium
import pandas as pd

# 读取数据
city_info = pd.read_csv('df_loc.csv')  
fruit_stores = pd.read_csv('df_customer.csv')  
facilities = pd.read_csv('df_wh.csv')  
city_names = pd.read_csv('df_list.csv', encoding='gbk')

# 合并城市信息和中文名称
city_info = pd.merge(city_info, city_names, on="Location", how="left")

# 创建地图
m = folium.Map(location=[35, 110], zoom_start=5)

# 标注水果店的位置和权重
store_counts = fruit_stores['Location'].value_counts()
for city, count in store_counts.items():
    city_data_df = city_info[city_info['Location'] == city]
    if not city_data_df.empty:
        city_data = city_data_df.iloc[0]
        folium.CircleMarker(
            location=[city_data['Latitude'], city_data['Longitude']],
            radius=5 + count,  # 根据水果店的数量调整点的大小
            color='red',
            fill=True,
            fill_color='red',
            fill_opacity=0.6,
            popup=f"{city_data['中文名称']} 水果店数: {count}",
        ).add_to(m)
    else:
        print(f"Warning: No data found for city {city}")


# 标注CDC和RDC的位置
for idx, facility in facilities.iterrows():
    city_data = city_info[city_info['Location'] == facility['Location']].iloc[0]
    color = 'blue' if facility['Type'] == 'CDC' else 'green'
    folium.Marker(
        location=[city_data['Latitude'], city_data['Longitude']],
        popup=f"{facility['Name']} ({facility['Type']})",
        icon=folium.Icon(color=color),
    ).add_to(m)

# 在地图上标注城市名称
for idx, city in city_info.iterrows():
    folium.Marker(
        location=[city['Latitude'], city['Longitude']],
        icon=folium.DivIcon(html=f"<div style='font-size: 12px; color: black;'>{city['中文名称']}</div>"),
    ).add_to(m)

# 显示地图
m.save("city_map.html")
m
