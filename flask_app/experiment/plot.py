import json
from datetime import timedelta, datetime
import plotly.graph_objs as go


def plot_culture(culture, limit=100000):
    ods, mus = culture.get_last_ods(limit=limit)
    gens, concs = culture.get_last_generations(limit=limit)
    od_threshold = culture.parameters["od_threshold"]
    vf = culture.parameters["volume_fixed"]
    va = culture.parameters["volume_added"]
    dilution_factor = (vf + va)/vf
    stress_increase_delay_generations = culture.parameters["stress_increase_delay_generations"]
    # semitransparent thin red horizontal lines every stress_increase_delay_generations
    stress_decrease_delay_hrs = culture.parameters["stress_decrease_delay_hrs"]

    if len(ods) == 0:
        trace1 = go.Scattergl(
            x=[],
            y=[],
            mode='markers',
            marker=dict(
                color='black'
            ),
            name='Optical Density',
            yaxis='y1'  # Set to the first y-axis
        )
    else:
        trace1 = go.Scattergl(
            x=list(ods.keys()),
            y=list(ods.values()),
            mode='markers',
            marker=dict(
                color='black'
            ),
            name='Optical Density',
            yaxis='y1')

    trace2 = go.Scattergl(
        x=list(gens.keys()),
        y=list(gens.values()),
        mode='lines+markers',
        line=dict(
            color='red',
            shape='linear',
        ),
        name='Generation',
        yaxis='y2'  # Set to the second y-axis
    )

    trace3 = go.Scattergl(
        x=list(concs.keys()),
        y=list(concs.values()),
        mode='lines+markers',
        line=dict(
            color='green',
            shape='hv',
        ),
        name='Concentration',
        yaxis='y3'  # Set to the third y-axis
    )
    if len(mus) > 0:
        trace4 = go.Scattergl(
            x=list(mus.keys()),
            y=list(mus.values()),
            mode='markers',
            line=dict(
                color='blue',
                shape='linear',
            ),
            name='Growth Rate',
            yaxis='y4'  # Set to the fourth y-axis
        )
    else:
        trace4 = go.Scattergl(
            x=[],
            y=[],
            mode='markers',
            line=dict(
                color='blue',
                shape='linear',
            ),
            name='Growth Rate',
            yaxis='y4'  # Set to the fourth y-axis
        )
    import pprint
    pp = pprint.PrettyPrinter(indent=4)
    pretty_parameters = pp.pformat(culture.parameters.inner_dict)
    pretty_parameters = pretty_parameters.replace('\n', '<br>')

    try:
        xp = list(ods.keys())[0]
        yp = list(ods.values())[0]+0.01
    except IndexError:
        xp = datetime.now()
        yp = 0.01

    params_trace = go.Scattergl(
        x=[xp],  # Place it at the earliest time point
        y=[yp],  # Place it at the minimum OD
        mode='markers',
        marker=dict(
            size=0,  # Set marker size to zero to make it invisible
        ),
        hovertext=[pretty_parameters],  # Show parameters on hover
        name='Parameters',
        yaxis='y1',  # Align it with the first y-axis
    )

    # Add lines
    lines = []
    # rescue_dilution lines
    if len(concs.values()) > 0:
        next_rescue_dilution_time = max(ods.keys()) + timedelta(hours=stress_decrease_delay_hrs)
        lines.append(go.layout.Shape(
            type="line",
            xref="x", yref="y3",  # Use 'y3' to align with concs trace
            x0=list(concs.keys())[-1], y0=list(concs.values())[-1],
            x1=next_rescue_dilution_time, y1=list(concs.values())[-1],
            line=dict(
                color="green",
                width=1,
                dash="dot",
            )
        ))
        lines.append(go.layout.Shape(
            type="line",
            xref="x", yref="y3",  # Use 'y3' to align with concs trace
            x0=next_rescue_dilution_time, y0=list(concs.values())[-1],
            x1=next_rescue_dilution_time, y1=list(concs.values())[-1]/dilution_factor,
            line=dict(
                color="green",
                width=1,
                dash="dot",
            )
        ))
    if len(ods.keys()) > 0:
        latest_od_x = max(ods.keys())
    else:
        latest_od_x = datetime.now()
    # od_threshold line
    lines.append(go.layout.Shape(
        type="line",
    xref="x", yref="y1",  # Use 'y1' to align with ods trace
    x0=latest_od_x, y0=od_threshold, x1=latest_od_x+timedelta(hours=12), y1=od_threshold,
    line=dict(
        color='rgba(0, 0, 0, 0.2)',
        width=4,
        dash="solid",
    )
    ))

    layout = go.Layout(
        title="Culture: " + str(culture.vial) + "<br>Experiment: "+culture.experiment.model.name,
        # annotations=[
        #     dict(
        #         x=0,
        #         y=0,
        #         showarrow=False,
        #         text=pretty_parameters,
        #         xref="paper",
        #         yref="paper",
        #         align='center'
        #     )
        # ],
        xaxis=dict(
            title='Time',
        ),
        yaxis=dict(
            title='Optical Density',
            automargin=True
        ),
        yaxis2=dict(
            title='Generation',
            overlaying='y',
            side='right',
            automargin=True,
        ),
        yaxis3=dict(
            title='Concentration',
            overlaying='y',
            side='left',
            position=0.97,
            automargin=True,
        ),
        yaxis4=dict(
            title='Growth Rate',
            overlaying='y',
            side='right',
            position=0.03,
            automargin=True,
        ),
        # shapes=lines,  # Add the lines to the layout
    )

    fig = go.Figure(data=[trace1, trace2, trace3, trace4, params_trace], layout=layout)
    return fig