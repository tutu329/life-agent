from dash import Dash, dcc, html, callback, Output, Input, State, CeleryManager
from dash_server.utils import Header, make_dash_table

import pandas as pd
import pathlib

# get relative data folder
PATH = pathlib.Path(__file__).parent

def create_layout(app):
    # Page layouts
    return html.Div(
        [
            html.Div([Header(app)]),
            html.Div(
                [
                    html.Div(
                        [
                            html.H5("新年快乐"),
                            html.Br([]),
                            html.P("说些什么...", id='history', ),
                        ],
                        className="pretty_container seven columns",
                    ),
                    html.Div(
                        [
                            html.H5("新年快乐"),
                            html.Br([]),
                            html.P("说些什么...", id='history', ),
                        ],
                        className="pretty_container five columns",
                    ),
                ],
                className="row flex-display",
                style={"margin-left": "1%"},
            ),
        ],
        className="page",
    )
