import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State, MATCH, ALL
from dash.exceptions import PreventUpdate
import dash_table
import pandas as pd
import base64
import io
import json
from pydub import AudioSegment
from helper_stuff import to_sub

# maybe i should write docs for this bc i dont wanna work on functionality right now

# this is just the columns of the dataframe the user is making
# its currently a global but will be move to a local store in deployment
header_df = pd.DataFrame(columns=['character', 'time_start', 'time_end', 'tone', 'transcript'])

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
        # data[start, end]
        dcc.Store(id='out_df', storage_type='session', data=header_df.to_json(date_format='iso', orient='split')),
        dcc.Store(id='data', storage_type='session', data={'start_raw': 0, 'end_raw': 0, 'start': 0, 'end': 0}),
        dcc.Store(id='idx', storage_type='session', data={'index': 0}),
        # maybe use this to store the dataframes instead

        # upload mp3 and subtitle srt files
        # the mp3 is going to need to be sent to a bucket with a life cycle
        dcc.Upload(
            id='upload-mp3',
            children=html.Div([
                html.A('Select Episode mp3 file')
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            # Allow multiple files to be uploaded
            multiple=True
        ),

        dcc.Upload(
            id='upload-data',
            children=html.Div([
                html.A('Select Subtitles SRT file')
            ]),
            style={
                'width': '100%',
                'height': '60px',
                'lineHeight': '60px',
                'borderWidth': '1px',
                'borderStyle': 'dashed',
                'borderRadius': '5px',
                'textAlign': 'center',
                'margin': '10px'
            },
            # Allow multiple files to be uploaded
            multiple=True
        ),

        # i don't know why i made this
        # i think it can be use to hold the index of the audio clip or something
        # html.Div(id='output-data-upload'),

        html.H3("Audio Labeler",
                style={'text-align': 'center'}),
        # audio out trying to add pause feature that will update the time clip
        # look into n_click_timestamp https://dash.plotly.com/dash-html-components/audio
        dbc.Row(
            # src = clip

            html.Audio(id='audio_out', controls=True, style={'display': 'block', 'margin': '0 auto'}, n_clicks=0)
        ),
        dbc.Row(
            [
                dbc.Col(dbc.Button('Click for Start time', id='get_start')),
                dbc.Col(dbc.Button('Click for End time', id='get_end'))
            ]
        ),

        # how much to offset the time gotten from the subtitle file
        dbc.Row(
            [
                dbc.Col(dbc.Input(id='start_offset', value=0, placeholder='start time offset', type="number",
                                  debounce=True)),
                dbc.Col(
                    dbc.Input(id='end_offset', value=0, placeholder='end time offset', type="number", debounce=True))
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
                dbc.Col(dbc.Button('Save & Next', id='save')),
                dbc.Col(dbc.Button('Skip', id='skip')),
            ]
        ),
        # where the out_df should be displayed
        html.Div(id='fake'),
        dash_table.DataTable(id='table', columns=[{"name": i, "id": i} for i in header_df.columns], editable=True)

    ], className="p-5"
)


def parse_contents(contents, filename, date):
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    # print(io.BytesIO(decoded.decode('utf-8')))
    # print(decoded)

    try:
        with io.BytesIO(decoded) as buffer:
            sb = io.TextIOWrapper(buffer, 'utf-8', newline='')
            # print(sb.read())
            sub_df = to_sub(sb)

    except Exception as e:
        print(e)
        return pd.DataFrame()
        # return html.Div([
        #     'There was an error processing this file.'
        # ])
    return sub_df


# todo re-wirte as it shouldn't be at the bottom just a test to make sure im parsing the data correctly
# the data should be in a stored obj
# @app.callback(Output('table_div', 'children'),
#               Input('upload-data', 'contents'),
#               State('upload-data', 'filename'),
#               State('upload-data', 'last_modified'))
# def update_output(list_of_contents, list_of_names, list_of_dates):
#     if list_of_contents is not None:
#         children = [parse_contents(c, n, d) for c, n, d in zip(list_of_contents, list_of_names, list_of_dates)]
#
#         out_table = dash_table.DataTable(id='table', columns=[{"name": i, "id": i} for i in children[0].columns],
#                                          data=children[0].to_dict('records'))
#
#         return out_table


# decodes the mp3 to byte code and saves it to a file now i can open the file as a buffer
# and open it with the audio segmentation thing
def parse_mp3_upload(contents):
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    with io.BytesIO(decoded) as buffer:
        clip = AudioSegment.from_mp3(buffer)
        # clip[10000:30000].export("10secs.mp3", format="mp3")
        # this works now how do i get it from here to the screen without saving it


# store the uploaded mp3 to store local object
# the test can be if i can hear it in the audio button
# @app.callback(Output('mp3_session', 'data'),
#               Input('upload-mp3', 'contents'),
#               State('upload-mp3', 'filename'),
#               State('upload-mp3', 'last_modified'),
#               State('mp3_session', 'data'))
# def update_output(list_of_contents, list_of_names, list_of_dates, data):
#     # print('Hello?')
#     if list_of_contents is not None:
#         print(list_of_names)
#         #parse_mp3_upload(list_of_contents[0])
#         # Give a default data dict with 0 clicks if there's no data.
#         data = data or {'mp3': 0}
#         data['mp3'] = list_of_contents[0]
#         return data
#     else:
#         raise PreventUpdate


@app.callback(Output('audio_out', 'src'),
              Output('data', 'data'),
              Input('end_offset', 'value'),
              Input('start_offset', 'value'),
              State('idx', 'data'),
              State('data', 'data'))
def chop_audio(end_offset, start_offset, idx, data):
    idx = idx or {'index': 0}
    index = idx['index']
    # print('idx:',index)
    data['start_raw'] = sub_df.TimeStart.iloc[index]
    data['end_raw'] = sub_df.TimeEnd.iloc[index]

    data['start'] = data['start_raw'] + start_offset
    data['end'] = data['end_raw'] + end_offset
    convert_file = clip[data['start']:data['end']].export(format="wav")

    out = base64.b64encode(convert_file.read()).decode('ascii')
    out = 'data:audio/wav;base64,' + out

    data['index'] = index
    return out, data


# so that when you click it get the correct offset
# but now the audio src doesnt update when i click next or skip
# how can i reset offset to zero when clicked
# how can i tell what the last clicked button was in javascript?
# i can make another dictionary that hold all the previous n_clicks counts but like no

# return changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
# return data['start'] - data['start_raw'] + ~~(document.getElementById("audio_out").currentTime * 1000) ;
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
    Output('start_offset', 'value'),
    Input('get_start', 'n_clicks'),
    Input('idx', 'data'),
    State('data', 'data')
)

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
    Output('end_offset', 'value'),
    Input('get_end', 'n_clicks'),
    Input('idx', 'data'),
    State('data', 'data')
)


# Save Button and functionality
# everything function but i cant break it up bc they both need these two outputs

@app.callback(Output('out_df', 'data'),
              Output('idx', 'data'),
              Input('save', 'n_clicks'),
              Input('skip', 'n_clicks'),
              Input('table', 'data'),
              State('data', 'data'),
              State('idx', 'data'),
              State('transcript', 'value'),
              State('char-dd', 'value'),
              State('tone', 'value'),
              State('out_df', 'data'))
def save_line(save_but, skip_but,table_data, data, idx, transcription, character, tone, df_store ):
    # if the save button was clicked or the skip button was clicked
    data = data or {'start_raw': 0, 'end_raw': 0, 'start': 0, 'end': 0}
    #
    idx = idx or {'index': 0}
    changed_id = [p['prop_id'] for p in dash.callback_context.triggered][0]
    if 'save' in changed_id:
        # take all the information and turn it to a df row to append
        # how should i get the time stamps + offsets to here?
        # solutions i can save it int the stores data
        row = {'character': character, 'time_start': data['start'], 'time_end': data['end'], 'tone': tone,
               'transcript': transcription}

        # append this row to the df
        out_df = pd.read_json(df_store, orient='split')
        out_df = out_df.append(row, ignore_index=True)

        # test
        out_df.to_csv('out.csv')

        # inc and return the new out_df
        idx['index'] = idx['index'] + 1
        return out_df.to_json(date_format='iso', orient='split'), idx

    elif 'skip' in changed_id:
        # inc but just return the unchanged df_store
        idx['index'] = idx['index'] + 1
        return df_store, idx

    elif 'table' in changed_id:
        # re-save over the out_df
        out_df = pd.DataFrame(table_data)
        return out_df.to_json(date_format='iso', orient='split'), idx

    else:
        return df_store, idx


# when a new row is appended update the table
@app.callback(Output('table', 'data'),
              Input('out_df', 'data'))
def table_update(df_store):
    df = pd.read_json(df_store, orient='split')
    data = df.to_dict('records')
    return data


# so this is the reload function that is called after the save&next or skip button is clicked
# Should i clear all the fields? ehh like yeah def
# not the dropdown tho which is good because i don't kow how i would do that
@app.callback(Output('transcript', 'value'),
              Output('tone', 'value'),
              Input('idx', 'data'))
def next_transcription(idx):
    idx = idx or {'index': 0}
    index = idx['index']
    line = sub_df.Text.iloc[index]
    return line, ''


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
