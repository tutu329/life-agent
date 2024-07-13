# -*- coding: utf-8 -*-
import time

import dash
from dash import Dash, dcc, html, Input, Output, State, callback, CeleryManager, set_props, clientside_callback
from dash.dependencies import Input, Output
from dash_server.pages import (
    overview,
    pricePerformance,
    portfolioManagement,
    feesMins,
    distributions,
    newsReviews,
)

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

app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width"}],
    # background_callback_manager = background_callback_manager,
)
app.title = "Financial Report"
server = app.server



# @callback(
#     Output('output', 'children'),
#     Input('submit-button', 'n_clicks'),
#     State('llm-input', 'value'),
#     # background=True,
# )
# def update_output(n_clicks, input1):
#     s = input1
#     # s = '你是一个最美丽的人，那么你到底是谁，又或者你来自哪里？'
#     length=len(input1)
#     ss = s
#     for i in range(length):
#         ss = s[:i]
#         time.sleep(0.1)
#         print(ss)
#         set_props(
#             component_id = "output",
#             props = {
#                 'children':ss,
#                 'style':{"color": "#ff0000"},
#             },
#         )
#
#     return ss

# console.log(dash_clientside.callback_context);
# dash_clientside.set_props(
#     "output",
#     {
#         'children': input1,
#         'style': {"color": "#ff0000"},
#     },
# )
# return dash_clientside.no_update;

# Describe the layout/ UI of the app
app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        html.Div(id="page-content"),
        # html.P("你是谁111？", id='output', ),
        # dcc.Input(id='llm-input', type='text', value='请输入你的问题...'),
        # html.Button(id='submit-button', n_clicks=0, children='提交'),
    ]
)

app.clientside_callback(
    """
    function(n_clicks, state) {
        var input1 = state
        console.log('-----------------1------------------');
        console.log(input1);
        console.log(input1.length);
        for (let i = 0; i < input1.length; i++) {
            setTimeout(() => {
                var out_s = input1.slice(0,i)
                console.log(out_s);
                dash_clientside.set_props(
                    "output",
                    {
                        'children': out_s,
                        'style': {"color": "#ffffff"},
                    },
                )
            }, i*10); // 10毫秒

        }
        return dash_clientside.no_update;
    }
    """,
    Output('output', 'children'),
    Input('submit-button', 'n_clicks'),
    State('llm-input', 'value'),
)

# Update page
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