# Optimizing Fresh Warehouse Networks Using MIP and SARIMA Forecasting

Mingyu Qi, Jingying Chen, and Yunlong Yang(B)  
Zhejiang University, Hangzhou 310058, China  
{15988288007,19357571847,aetheryyl}@163.com  

## Abstract
The rapid expansion of fresh produce e-commerce demands efficient warehouse network optimization. This paper employs mixed-integer programming (MIP) to minimize logistics costs and uses the Seasonal Autoregressive Integrated Moving Average (SARIMA) model [1] for order forecasting. For the static warehouse network layout, we formulate an MIP model using order demand data. By applying the branch-and-bound method with the Gurobi solver, we determine the optimal logistics plans, resulting in 6 RDC’s (8 warehouses) and a total logistics cost of 9.9029 million yuan. For order forecasting, we compare the Error-Trend-Seasonality (ETS), Random Forest, and SARIMA models, selecting SARIMA for its superior accuracy with an 80/20 training-validation split. For the dynamic multi-period layout, we simulate demand using an empirical distribution function (EDF) with fluctuations. By integrating short-term historical data analysis and long-term forecast validation, we identify 6 robust, mandatory RDC’s locations.

## Keywords
Mixed-Integer Programming · Seasonal Autoregressive Integrated Moving Average · Empirical Distribution Function
