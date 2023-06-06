from datetime import timedelta, datetime
import plotly.graph_objs as go


def plot_culture(culture, limit=100000):
    ods = culture.get_last_ods(limit=limit)
    gens, concs = culture.get_last_generations(limit=limit)

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
        fig = go.Figure(data=[trace1])
        return fig

    od_threshold = culture.parameters["od_threshold"]
    vf = culture.parameters["volume_fixed"]
    va = culture.parameters["volume_added"]
    dilution_factor = (vf + va)/vf
    stress_increase_delay_generations = culture.parameters["stress_increase_delay_generations"]
    # semitransparent thin red horizontal lines every stress_increase_delay_generations
    stress_decrease_delay_hrs = culture.parameters["stress_decrease_delay_hrs"]
    next_rescue_dilution_time = max(ods.keys()) + timedelta(hours=stress_decrease_delay_hrs)
    next_rescue_dilution_time = None

    trace1 = go.Scattergl(
        x=list(ods.keys()),
        y=list(ods.values()),
        mode='markers',
        marker=dict(
            color='black'
        ),
        name='Optical Density',
        yaxis='y1'  # Set to the first y-axis
    )

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

    # Add horizontal lines
    lines = []
    # gen = min(gens.values())
    # while gen <= max(gens.values()) + 1:
    #     gen += stress_increase_delay_generations
    #     lines.append(go.layout.Shape(
    #         type="line",
    #         xref="paper", yref="y2",  # Use 'y2' to align with gens trace
    #         x0=0, y0=gen, x1=1, y1=gen,
    #         line=dict(
    #             color='rgba(255, 0, 0, 0.2)',
    #             width=1,
    #             dash="dot",
    #
    #         )
    #     ))
    # rescue_dilution lines
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
    latest_od_x = max(ods.keys())
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
    print("2")

    layout = go.Layout(
        title="Culture " + str(culture.vial),
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
            # position=0.05,
            automargin=True,
        ),
        # shapes=lines,  # Add the lines to the layout
    )

    fig = go.Figure(data=[trace1, trace2, trace3], layout=layout)
    return fig