import dash
from dash import dcc, html, dash_table
import plotly.express as px
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, MATCH, ALL
from dash.exceptions import PreventUpdate
import pandas as pd
import numpy as np
import base64
import io
import json
from pydub import AudioSegment
from helper_stuff import to_sub
from audio_graph import get_fig
from scipy import signal

# this is just the columns of the dataframe the user is making
# its currently a global but will be move to a local store in deployment

header_df = pd.DataFrame(columns=['sub_idxs', 'character', 'time_start', 'time_end', 'tone', 'transcript'])

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# the list of characters for dropdown menu hard coded make as input for generalization of other shows
characters = ['Rick', 'Morty', 'Jerry', 'Summer', 'Beth']
char_options = [{'label': x, 'value': x} for x in characters]

# temp test audio and subtitles file to use for functionality testing
clip = AudioSegment.from_mp3('/Users/mazzeogeorge/Code/Audio-labler/assests/rick_temp/S01E03 - Anatomy Park.mp3')

subtitles_file = '/Users/mazzeogeorge/Code/Audio-labler/assests/rick_temp/Rick.and.Morty.S01E03.720p.BluRay.x264.DAA.srt'
sub_df = to_sub(subtitles_file)

app.layout = dbc.Container(
    [
        # idx['index'] is index of df to inc with next and skip
        # out_df['out_df'] output dataframe with columns=['character', 'time_start', 'time_end', 'tone', 'transcript']
        # timestamp[start, end]
        html.Div(id='tmp'),
        dcc.Store(id='out_df', storage_type='memory', data=header_df.to_json(date_format='iso', orient='split')),
        dcc.Store(id='timestamp', storage_type='memory',
                  data={'start_raw': 0, 'end_raw': 0, 'start': 0, 'end': 0, 'index': 0}),
        dcc.Store(id='idx', storage_type='memory', data={'index': 0, 'current_indexes': [0]}),

        html.H3("Audio Labeler", style={'text-align': 'center'}),

        dbc.Row(
            # src = clip

            html.Audio(id='audio_out', controls=True, style={'display': 'block', 'margin': '0 auto'}, n_clicks=0)

        ),
        dbc.Row([

            dcc.Graph(id='sound_graph'),
            dcc.Interval(id='timer', interval=200, n_intervals=0),
            dcc.Store(id='timer_mem', storage_type='memory', data={'last_callback': 0})
        ]),

        dbc.Row(
            [
                dbc.Col(dbc.Button('Click for Start time', id='get_start_btn')),
                dbc.Col(dbc.Button('Click for End time', id='get_end_btn'))
            ]
        ),

        # how much to offset the time gotten from the subtitle file
        dbc.Row(
            [
                dbc.Col(dbc.Input(id='start_offset_input', value=0, placeholder='start time offset', type="number",
                                  debounce=True)),
                dbc.Col(
                    dbc.Input(id='end_offset_input', value=0, placeholder='end time offset', type="number",
                              debounce=True))
            ]
        ),
        # the transcription of the audio file
        dbc.Row(
            [
                dbc.Col(dbc.Input(id='transcript', placeholder='transcription'))
            ]
        ),
        # character dropdown and tone notes
        dbc.Row(
            [
                dbc.Col(dcc.Dropdown(id='char-dd', options=char_options, value=characters[0])),
                dbc.Col(dbc.Input(id='tone', placeholder='tone/notes')),
            ]
        ),
        # save the clip to the out_df or skip that time stamp
        dbc.Row(
            [
                # dbc.Col(dbc.Button('Prev', id='prev')),
                dbc.Col(dbc.Button('Save & Next', id='save_btn')),
                dbc.Col(dbc.Button('Skip', id='skip_btn')),
            ]
        ),
        # where the out_df should be displayed
        html.P(id='nex_line_preview'),
        html.Audio(id='next_audio_out_preview', controls=True, style={'display': 'block', 'margin': '0 auto'},
                   n_clicks=0,),
        dbc.Button('include to current and view next line preview', id='add_preview_btn'),

        dash_table.DataTable(id='table', columns=[{"name": i, "id": i} for i in header_df.columns], editable=True)

    ], className="p-5"
)


@app.callback(Output('audio_out', 'src'),
              Output('timestamp', 'data'),
              Output('sound_graph', 'figure'),
              Input('end_offset_input', 'value'),
              Input('start_offset_input', 'value'),
              State('idx', 'data'),
              State('timestamp', 'data'))
def chop_audio(end_offset_input, start_offset_input, idx, timestamp):
    idx = idx or {'index': 0, 'current_indexes': [0]}
    index = idx['index']
    if end_offset_input is None:
        end_offset_input = 0
    if start_offset_input is None:
        start_offset_input = 0

    if len(idx['current_indexes']) == 1:
        # print('new transcription')
        timestamp['start_raw'] = sub_df.TimeStart.iloc[index]
        timestamp['end_raw'] = sub_df.TimeEnd.iloc[index]

        timestamp['start'] = timestamp['start_raw'] + start_offset_input
        timestamp['end'] = timestamp['end_raw'] + end_offset_input


    else:
        # print('continuation')
        timestamp['end_raw'] = sub_df.TimeEnd.iloc[index]
        timestamp['end'] = timestamp['end_raw'] + end_offset_input
        #not going to touch the start just going to append the TimeEnd of the new index to the current one

    # must down sample for graph
    audio_clip = clip[timestamp['start']:timestamp['end']].export(format="wav")
    graph_clip = clip[timestamp['start']:timestamp['end']].export(format="wav", parameters=["-ac","2","-ar","4000"])

    audio_data = audio_clip.read()
    out = base64.b64encode(audio_data).decode('ascii')
    out = 'data:audio/wav;base64,' + out

    # fr = clip.frame_rate
    # audio_amps = np.frombuffer(graph_clip.read(), dtype="int16")
    audio_amps = np.frombuffer(audio_data, dtype="int16")
    downsampled = signal.resample(audio_amps, int(len(audio_amps)/2**6))
    print(len(audio_amps), 'len small')

    df_sound = pd.DataFrame(dict(
        y=downsampled
    ))

    return out, timestamp, get_fig(df_sound)


@app.callback(Output('tmp', 'children'),
              Output('timer_mem', 'data'),
              Input('sound_graph', 'relayoutData'),
              State('timer', 'n_intervals'),
              State('timer_mem', 'data'))
def print_figure(time_bounds, timer, timer_mem):
    # how to check if it was just triggered less than half a second ago??
    last_call = timer_mem['last_callback']
    print(time_bounds, timer, last_call)
    if last_call >= timer - 5:
        raise PreventUpdate
    else:
        print('change', time_bounds)
    return str(time_bounds), {'last_callback': timer}


# data['index'] is the updated index from chopping the audio if they are equal then chop_audio was last call
# if they are not equal then something changed the index but it wasn't chop_audio something with get_start

# return changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
# return data['start'] - data['start_raw'] + ~~(document.getElementById("audio_out").currentTime * 1000) ;
# When you press the get_start_btn this function updates the start_offset input similar for the end_btn
app.clientside_callback(
    """
    function(largeValue1, idx, data) {
        if (idx['index'] == data['index']) {
            return data['start'] - data['start_raw'] + ~~(document.getElementById("audio_out").currentTime * 1000) ;
        } else {
            return 0
        }
    }
    """,
    Output('start_offset_input', 'value'),
    Input('get_start_btn', 'n_clicks'),
    Input('idx', 'data'),
    State('timestamp', 'data')
)

# but when you press the add_preview_btn it should update the end_offset_input to the newest end here
app.clientside_callback(
    """
    function(largeValue1, idx, data) {
        if (idx['index'] == data['index']) {
            return data['start'] - data['end_raw'] + ~~(document.getElementById("audio_out").currentTime * 1000);
        } else {
            return 0
        }
    }
    """,
    Output('end_offset_input', 'value'),
    Input('get_end_btn', 'n_clicks'),
    Input('idx', 'data'),
    State('timestamp', 'data')
)


# Save Button and functionality
# everything function but i cant break it up bc they both need these two outputs

@app.callback(Output('out_df', 'data'),
              Output('idx', 'data'),
              Output('table', 'data'),
              Input('save_btn', 'n_clicks'),
              Input('skip_btn', 'n_clicks'),
              Input('add_preview_btn', 'n_clicks'),
              State('timestamp', 'data'),
              State('idx', 'data'),
              State('transcript', 'value'),
              State('char-dd', 'value'),
              State('tone', 'value'),
              State('out_df', 'data'))
def save_line(save_btn, skip_btn, add_preview_btn, timestamp, idx, transcription, character, tone, df_store):
    # if the save button was clicked or the skip button was clicked
    timestamp = timestamp or {'start_raw': 0, 'end_raw': 0, 'start': 0, 'end': 0}

    idx = idx or {'index': 0, 'current_indexes': [0]}
    print('save_line', idx)
    # print(df_store)
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]

    out_df = pd.read_json(df_store, orient='split')
    table = out_df.to_dict('records')

    if 'save' in changed_id:
        # take all the information and turn it to a df row to append
        # how should i get the time stamps + offsets to here?
        # solutions i can save it int the stores data

        row = {'sub_idxs': str(idx['current_indexes']), 'character': character, 'time_start': timestamp['start'],
               'time_end': timestamp['end'], 'tone': tone,
               'transcript': transcription}

        # append this row to the df

        out_df = out_df.append(row, ignore_index=True)

        # test
        out_df.to_csv('out.csv')

        # inc and return the new out_df
        idx['index'] = idx['index'] + 1
        idx['current_indexes'] = [idx['index']]

        new_table = out_df.to_dict('records')
        print(out_df)
        return out_df.to_json(date_format='iso', orient='split'), idx, new_table

    elif 'skip' in changed_id:
        # inc but just return the unchanged df_store
        idx['index'] = idx['index'] + 1
        return df_store, idx, table

    elif 'add_preview_btn' in changed_id:
        # so we need to update preview_line and preview_audio_out
        # also keep track for index list
        idx['index'] = idx['index'] + 1
        idx['current_indexes'].append(idx['index'])

        return df_store, idx, table


    else:
        return df_store, idx, table


# so this is the reload function that is called after the save&next or skip button is clicked
# Should i clear all the fields? ehh like yeah
# not the dropdown tho which is good because i don't kow how i would do that

# can i add a way to add the next transcription line too like if i should connect them?
# what if i add another input ? to change the idx?
@app.callback(Output('transcript', 'value'),
              Output('tone', 'value'),
              Output('nex_line_preview', 'children'),
              Output('next_audio_out_preview', 'src'),

              Input('idx', 'data'),
              State('transcript', 'value'),
              State('tone', 'value'))
def next_transcription(idx, tran_line, tone):
    idx = idx or {'index': 0, 'current_indexes': [0]}
    index = idx['index']
    if len(idx['current_indexes']) == 1:
        # if there is only index in current index after the index changed its a new transcription
        # print('new transcription')
        line = sub_df.Text.iloc[index]
        tone = ''
    else:
        # print('continuation')
        # current line + nex line
        line = tran_line + ' ' + sub_df.Text.iloc[index]
        # else continuation


    if index + 1 <= len(sub_df):
        next_line = sub_df.Text.iloc[index + 1]
        audio_clip = clip[sub_df.TimeStart.iloc[index + 1]:sub_df.TimeEnd.iloc[index + 1]].export(format="wav")
        audio_clip_data = audio_clip.read()
        next_out_preview = base64.b64encode(audio_clip_data).decode('ascii')
        next_out_preview = 'data:audio/wav;base64,' + next_out_preview

    else:
        next_line = "END OF FILE - it'sa good show"
        next_out_preview = ''

    return line, tone, next_line, next_out_preview


# collapse functionality to drop down the the data table
# collapse = html.Div(
#     [
#         dbc.Button(
#             "Open collapse",
#             id="collapse-button",
#             className="mb-3",
#             color="primary",
#         ),
#         dbc.Collapse(
#             dbc.Card(dbc.CardBody("This content is hidden in the collapse")),
#             id="collapse",
#         ),
#     ]
# )
#
#
# @app.callback(
#     Output("collapse", "is_open"),
#     [Input("collapse-button", "n_clicks")],
#     [State("collapse", "is_open")],
# )
# def toggle_collapse(n, is_open):
#     if n:
#         return not is_open
#     return is_open


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')
