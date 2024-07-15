# -*- coding: utf-8 -*-
import time

import dash
from dash import Dash, dcc, html, Input, Output, State, callback, CeleryManager, set_props, clientside_callback, ClientsideFunction
from dash.dependencies import Input, Output
from dash_server.pages import (
    overview,
    pricePerformance,
    portfolioManagement,
    feesMins,
    distributions,
    newsReviews,
)
from dash_extensions.javascript import assign    # pip install dash-extensions
from config import dred, dgreen, dblue

# ---------------连接Celery和Redis服务，以启动background_callback_manager------------------
from celery import Celery
import redis
redis_url = 'redis://localhost:6379/0'
try:
    r = redis.from_url(redis_url)
    r.set('msg', 'connected.')
    dgreen(f'[Dash_Server] REDIS_URL="{redis_url}": "{r.get("msg").decode("utf-8")}"')
except Exception as e:
    dred(f'[Dash_Server] REDIS_URL="{redis_url}" connection failed: "{e}"')

celery_app = Celery(__name__, broker=redis_url, backend=redis_url)
background_callback_manager = CeleryManager(celery_app)
dgreen(f'[Dash_Server] background_callback_manager inited.')
# --------------------------------------------------------------------------------------

# Dash的配置
from flask import Flask, request

flask_server = Flask(__name__)
app = dash.Dash(
    __name__,
    server=flask_server,
    meta_tags=[
        {"name": "viewport", "content": "width=device-width"}
    ],
    # external_scripts=[
    #     'https://cdn.jsdelivr.net/npm/axios@1.2.0/dist/axios.min.js',
    #     'https://cdn.jsdelivr.net/npm/eventsource-parser@1.1.2/dist/index.js',
    # ],
    # background_callback_manager = background_callback_manager,
)
app.config["suppress_callback_exceptions"] = True   # 屏蔽一些callback找不到id的错误
app.title = "Financial Report"
server = app.server
print(f'flask server: {server}')




# flask_server.secret_key = 'your_secret_key'  # 设置密钥以启用 session 功能
# session_id = request.cookies.get('session')
# print(f'flask server session_id: {session_id}')


# 主页的html布局
app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        html.Div(id="page-content"),
    ]
)

# 'submit-button'按钮的callback(clientside回调, 主要解决stream输出的实时刷新问题，不经过server端)
# 'llm_client'和'ask_llm'均为llm_client.js中设置的名字
# 输入：
#   1) 按钮('submit-button')的'n_clicks'事件
#   2) input输入框('llm-input')的'value'值
# 输出：
#   html控件(id为'output')的'children'值
clientside_callback(
    ClientsideFunction(
        namespace='llm_client',
        function_name='ask_llm'
    ),
    Output('output', 'children'),
    Input('submit-button', 'n_clicks'),
    State('llm-input', 'value'),
    prevent_initial_call=True,
)

# 导航栏的callback
@app.callback(
    Output("page-content", "children"),
    [Input("url", "pathname")]
)
def display_page(pathname):
    if pathname == "/dash-financial-report/price-performance":
        return pricePerformance.create_layout(app)
    elif pathname == "/dash-financial-report/portfolio-management":
        return portfolioManagement.create_layout(app)
    elif pathname == "/dash-financial-report/fees":
        return feesMins.create_layout(app)
    elif pathname == "/dash-financial-report/distributions":
        return distributions.create_layout(app)
    elif pathname == "/dash-financial-report/news-and-reviews":
        return newsReviews.create_layout(app)
    elif pathname == "/dash-financial-report/full-view":
        return (
            overview.create_layout(app),
            pricePerformance.create_layout(app),
            portfolioManagement.create_layout(app),
            feesMins.create_layout(app),
            distributions.create_layout(app),
            newsReviews.create_layout(app),
        )
    else:
        return overview.create_layout(app)

if __name__ == "__main__":
    app.run_server(debug=True, host='0.0.0.0', port=7861)

