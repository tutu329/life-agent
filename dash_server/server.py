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
        # The memory store reverts to the default on every page refresh
        dcc.Store(id='mem'),
        # The local store will take the initial data
        # only the first time the page is loaded
        # and keep it until it is cleared.
        dcc.Store(id='local-mem', storage_type='local'),
        # Same as the local store but will lose the data
        # when the browser/tab closes.
        dcc.Store(id='session-mem', storage_type='session'),

        dcc.Location(id="url", refresh=False),
        html.Div(id="page-content"),
    ]
)

# 'submit-button'按钮的callback(clientside回调, 主要解决stream输出的实时刷新问题，不经过server端)
# 'llm_client'和'ask_llm'均为llm_client.js中设置的名字
# 输入：
#   1) 按钮('submit-button')的'n_clicks'事件
#   2) input输入框('llm-input')的'value'值
#   3) persistent量('local-mem')的'data'值
# 输出：
#   html控件(id为'output')的'children'值
clientside_callback(
    ClientsideFunction(
        namespace='llm_client',
        function_name='ask_llm'
    ),
    # Output('show_mem', 'children'),
    # Output('session-mem', 'data'),
    output=Output('output', 'children'),
    inputs=Input('submit-button', 'n_clicks'),
    state=[
        State('llm-input', 'value'),    # llm-input是输出参数
        State('local-mem', 'data'),     # local-mem是persistent量，交给callback，callback中会将结果保存到local-mem中
    ],
    prevent_initial_call=True,
)

# ----------------------dcc.Store为Dash的会话机制(非常重要和高效)----------------------
# dcc.Store作为input时，在on-page-load时，也会触发。（因此就不需要专门处理on-page-load了）
@callback(
    output=[Output('show_local_mem', 'children')],
    inputs=[
        Input('mem', 'data'),
        Input('local-mem', 'data'),
        Input('session-mem', 'data'),
    ],
    # 这里确保on-page-load时，被调用
    # prevent_initial_call=True,
)
def on_mem_change(mem, local_mem, session_mem):
    # ----------------------是否为on-page-load----------------------
    if mem is None:
        # ----------------------on-page-load-----------------------
        print(f'---------------------dcc.Store-------------------------', flush=True)
        print(f'mem: {mem!r}', flush=True)  # 刷新页面就会为None
        print(f'local-mem: {local_mem!r}', flush=True)  # persistent(常用，类似与浏览器对应的session_id会话)
        print(f'session-mem: {session_mem!r}', flush=True)  # persistent但是关闭浏览器标签时会为None
        print(f'-------------------------------------------------------', flush=True)

        # 1、设置page已经loaded的标识
        set_props("mem", {'data': 'page_loaded'})

        # 2、读取local-mem(这里就是通过后面的return，读取local-mem的值到html某个控件中)

        # ---------------------------------------------------------
    else:
        # 非on-page-load
        pass

    # 测试用的输出显示

    result = f'local-mem: {local_mem!r}'
    return [result]

# @callback(
#     Output('show_mem', 'children'),
#     Input('submit-button', 'n_clicks'),
#     State('local', 'data'),
#     prevent_initial_call=True,
# )
# def on_click(n_clicks, data):
#     # if n_clicks is None:
#     #     # prevent the None callbacks is important with the store component.
#     #     # you don't want to update the store for nothing.
#     #     raise PreventUpdate
#
#     # Give a default data dict with 0 clicks if there's no data.
#     # data = data or {'clicks': 0}
#     #
#     # data['clicks'] = data['clicks'] + 1
#     return data

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
    app.run_server(debug=True, host='0.0.0.0', port=5110)

