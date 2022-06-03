import plotly.graph_objects as go
import plotly.express as px

import pandas as pd



def get_fig(df):
    # Load data
    # df = pd.read_csv(
    #     "https://raw.githubusercontent.com/plotly/datasets/master/finance-charts-apple.csv")
    # df.columns = [col.replace("AAPL.", "") for col in df.columns]

    # Create figure
    fig = go.Figure()

    fig.add_trace(

        go.Scatter(y=list(df.y))
    )

    # Set title
    fig.update_layout(
        title_text="Time series with range slider and selectors. dont get to caught up "
                   "in the spikes its a compress audio that your hearing"

    )
    fig.layout.yaxis.fixedrange = True
    # Add range slider
    # fig.update_layout(
    #     xaxis=dict(
    #         rangeselector=dict(),
    #         rangeslider=dict(
    #             visible=True
    #         ),
    #         # type="date"
    #     )
    # )

    return fig


