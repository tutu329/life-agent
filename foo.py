import numpy as np
import pandas as pd
from scipy.optimize import curve_fit
import plotly.graph_objects as go
from plotly.offline import plot

# 原始数据
data = {
    "杭州市会负荷最大负荷（MW）": [18330.0, 19130.0, 20280.0, 22154.6],
    "萧山全社会负荷最大负荷（MW）": [3632.0, 3821.0, 3970.0, 4547.0],
    "萧山220kV网供最大负荷（MW）": [3533.0, 3655.0, 3600.0, 3890.0],
    "萧山110kV网供最大负荷（MW）": [2821.0, 2929.0, 3393.0, 3430.0],
    "萧山北部20千伏供区最大负荷（MW）": [256.2, 308.2, 368.8, 370.2],
    "萧山北部10千伏供区最大负荷（MW）": [508.0, 538.4, 578.5, 610.8],
    "萧山中部片区最大负荷（MW）": [1018.1, 1059.5, 1096.7, 1154.2],
    "萧山南部片区最大负荷（MW）": [457.5, 459.9, 476.5, 515.3],
    "萧山临空片区最大负荷（MW）": [515.5, 509.8, 537.6, 530.2],
    "萧山临空以东片区最大负荷（MW）": [342.4, 319.9, 330.8, 359.2]
}

years = np.array([2021, 2022, 2023, 2024])
future_years = np.arange(2025, 2031)  # 预测2025-2030


# 定义Logistic函数(以2024为拐点年)
# f(t) = d + a / (1 + exp(-b*(t - 2024)))
def logistic(t, a, b, d):
    return d + a / (1.0 + np.exp(-b * (t - 2024)))


fig = go.Figure()

for name, values in data.items():
    y = np.array(values)

    # 初始猜测参数
    guess_a = (max(y) - min(y))
    guess_b = 0.5
    guess_d = min(y) * 0.9

    # 拟合Logistic曲线
    popt, pcov = curve_fit(logistic, years, y, p0=[guess_a, guess_b, guess_d], maxfev=20000)
    a_fit, b_fit, d_fit = popt

    # 生成2021-2030年的平滑拟合曲线
    all_years = np.arange(2021, 2031)
    fitted_y = logistic(all_years, a_fit, b_fit, d_fit)

    # 历史数据点（2021-2024）
    fig.add_trace(go.Scatter(
        x=years,
        y=y,
        mode='markers',
        name=f"{name} 历史数据",
        marker=dict(size=6),
        legendgroup=name
    ))

    # 连续的拟合曲线（2021-2030）
    fig.add_trace(go.Scatter(
        x=all_years,
        y=fitted_y,
        mode='lines',
        name=f"{name} 拟合曲线",
        line=dict(width=2),
        legendgroup=name
    ))

    # 预测点（2025-2030），使用空心标记以示区分
    fig.add_trace(go.Scatter(
        x=future_years,
        y=logistic(future_years, a_fit, b_fit, d_fit),
        mode='markers',
        name=f"{name} 预测点(2025-2030)",
        marker=dict(symbol='circle-open', size=6),
        legendgroup=name,
    ))

# 美化图表
fig.update_layout(
    title="2030年各区域电力负荷预测",
    xaxis_title="年份",
    yaxis_title="负荷（MW）",
    hovermode="x unified",
    template="plotly_white",
    legend=dict(title="负荷类型")
)

# 输出图表
plot(fig, filename='output.html')
