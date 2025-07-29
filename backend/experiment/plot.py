import json
from datetime import timedelta, datetime
import plotly.graph_objs as go

from experiment.ModelBasedCulture.culture_growth_model import CultureGrowthModel


def plot_culture(culture, limit=100000, title=None):
    culture_parameters = culture.updater.__dict__

    if isinstance(culture, CultureGrowthModel):
        ods = {p[1]: p[0] for p in culture.population}
        mus = {p[1]: p[0] for p in culture.effective_growth_rates}
        concs = {p[1]: p[0] for p in culture.doses}
        gens = {p[1]: p[0] for p in culture.generations}
        rpms = {}
    else:
        # Extract data from real experiment
        ods, mus, rpms = culture.get_last_ods_and_rpms(limit=limit)
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
    if len(rpms) == 0:
        x_rpm = []
        y_rpm = []
    else:
        x_rpm = list(rpms.keys())
        y_rpm = list(rpms.values())
    trace5 = go.Scattergl(
        x=x_rpm,
        y=y_rpm,
        mode='markers',
        line=dict(
            color='orange',
            shape='linear',
        ),
        name='RPM',
        yaxis='y5'  # Set to the fifth y-axis
    )
    import pprint
    pp = pprint.PrettyPrinter(indent=4)
    pretty_parameters = pp.pformat(culture_parameters)
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

    layout = go.Layout(
        title=title if title else None,
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
        yaxis5=dict(
            title='RPM',
            overlaying='y',
            side='left',
            position=0.06,
            automargin=True,
        ),
    )
    fig = go.Figure(data=[trace1, trace2, trace3, trace4, trace5, params_trace], layout=layout)
    return fig


def plot_compare_metric(experiment, vials, metric='od', limit=100000):
    """
    Compare a specific metric across multiple vials
    
    Args:
        experiment: The experiment object
        vials: List of vial numbers to compare
        metric: Metric to plot ('od', 'growth_rate', 'concentration', 'generation', 'rpm')
        limit: Number of data points to include
    """
    
    # Define colors for consistent vial coloring
    vial_colors = {
        1: '#1f77b4',  # blue
        2: '#ff7f0e',  # orange
        3: '#2ca02c',  # green
        4: '#d62728',  # red
        5: '#9467bd',  # purple
        6: '#8c564b',  # brown
        7: '#e377c2',  # pink
    }
    
    # Define metric properties
    metric_config = {
        'od': {
            'title': 'Optical Density Comparison',
            'y_title': 'Optical Density',
            'mode': 'markers'
        },
        'growth_rate': {
            'title': 'Growth Rate Comparison',
            'y_title': 'Growth Rate (1/h)',
            'mode': 'markers'
        },
        'concentration': {
            'title': 'Drug Concentration Comparison',
            'y_title': 'Concentration (μg/mL)',
            'mode': 'lines+markers'
        },
        'generation': {
            'title': 'Generation Comparison',
            'y_title': 'Generation',
            'mode': 'lines+markers'
        },
        'rpm': {
            'title': 'Stirrer RPM Comparison',
            'y_title': 'RPM',
            'mode': 'markers'
        }
    }
    
    if metric not in metric_config:
        raise ValueError(f"Unknown metric: {metric}. Must be one of: {list(metric_config.keys())}")
    
    traces = []
    
    for vial in vials:
        if vial not in experiment.cultures:
            continue
            
        culture = experiment.cultures[vial]
        
        # Get data based on metric type
        if metric in ['od', 'growth_rate', 'rpm']:
            ods, mus, rpms = culture.get_last_ods_and_rpms(limit=limit)
            if metric == 'od':
                data_dict = ods
            elif metric == 'growth_rate':
                data_dict = mus
            else:  # rpm
                data_dict = rpms
                
        elif metric in ['concentration', 'generation']:
            gens, concs = culture.get_last_generations(limit=limit)
            if metric == 'generation':
                data_dict = gens
            else:  # concentration
                data_dict = concs
        
        if len(data_dict) > 0:
            # Get vial name from culture parameters
            try:
                vial_name = culture.parameters["name"]
            except (KeyError, AttributeError):
                vial_name = f"Vial {vial}"
            legend_name = f'Vial {vial} [{vial_name}]'
            
            trace = go.Scattergl(
                x=list(data_dict.keys()),
                y=list(data_dict.values()),
                mode=metric_config[metric]['mode'],
                name=legend_name,
                marker=dict(color=vial_colors.get(vial, '#000000')),
                line=dict(color=vial_colors.get(vial, '#000000'))
            )
            traces.append(trace)
    
    layout = go.Layout(
        title=metric_config[metric]['title'],
        xaxis=dict(title='Time'),
        yaxis=dict(title=metric_config[metric]['y_title']),
        showlegend=True
    )
    
    fig = go.Figure(data=traces, layout=layout)
    return fig