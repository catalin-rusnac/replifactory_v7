import json
import os
import csv
from collections import defaultdict
from pprint import PrettyPrinter


def clean_experiment_name(experiment_name):
    forbidden_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
    experiment_name = experiment_name.replace("/", "_")
    new_experiment_name = ''.join([char for char in experiment_name if char not in forbidden_chars])
    new_experiment_name = new_experiment_name.strip()
    if new_experiment_name != experiment_name:
        print(f"Experiment name {experiment_name} contains forbidden characters. Replacing with {new_experiment_name}")
        experiment_name = new_experiment_name
    return experiment_name


def export_culture_plot_html(culture, output_directory, predicted=False):
    experiment_name = culture.experiment.model.name
    vial = culture.vial
    if predicted:
        fig = culture.plot_predicted()
    else:
        fig = culture.plot_data()
    # clear experiment name from characters forbidden in file names such as !, ?, etc.
    experiment_name = clean_experiment_name(experiment_name)

    output_file = os.path.join(output_directory, experiment_name, 'vial_%d_plot.html' % int(vial))
    output_file = os.path.abspath(output_file)
    if not os.path.exists(os.path.dirname(output_file)):
        os.makedirs(os.path.dirname(output_file))
    fig.write_html(output_file)
    return output_file


def export_culture_csv(culture, output_directory):
    experiment_name = culture.experiment.model.name
    experiment_name = clean_experiment_name(experiment_name)

    vial = culture.vial
    ods, mus, rpms = culture.get_last_ods_and_rpms(limit=1000000)
    gens, concs = culture.get_last_generations(limit=1000000)

    # Combine all dictionaries into one
    combined = defaultdict(lambda: [None, None, None, None])  # Default value is a list of four None values

    for dt, value in ods.items():
        combined[dt][0] = value

    for dt, value in mus.items():
        combined[dt][1] = value

    for dt, value in gens.items():
        combined[dt][2] = value

    for dt, value in concs.items():
        combined[dt][3] = value

    # Create the output file path
    output_file = os.path.join(output_directory, experiment_name, 'vial_%d_data.csv' % int(vial))
    output_file = os.path.abspath(output_file)
    # Create the output directory if it doesn't exist
    if not os.path.exists(os.path.dirname(output_file)):
        os.makedirs(os.path.dirname(output_file))

    # Write data to the CSV file, sorted by datetime
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = ['Time', 'OD', 'mu', 'generation', 'concentration']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for dt in sorted(combined.keys()):
            writer.writerow({'Time': dt, 'OD': combined[dt][0], 'mu': combined[dt][1], 'generation': combined[dt][2],
                             'concentration': combined[dt][3]})
    print("Exported CSV file to %s" % output_file)
    return output_file


def export_parameters(experiment, output_directory):
    experiment_name = experiment.model.name
    experiment_name = clean_experiment_name(experiment_name)
    output_directory = os.path.join(output_directory, experiment_name)
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)

    output_file_txt = os.path.join(output_directory, "experiment_parameters.txt")
    output_file_json = os.path.join(output_directory, "experiment_parameters.json")

    with open(output_file_txt, "w+") as f:
        pp = PrettyPrinter(stream=f)
        pp.pprint(experiment.model.parameters)
    with open(output_file_json, "w+") as f:
        json.dump(experiment.model.parameters, f)