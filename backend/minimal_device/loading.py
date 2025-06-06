import inspect
import os
import pickle
import time

import numpy as np
import yaml


def load_config(obj, filepath):
    config = open(filepath).read()
    loaded_dict = yaml.load(config, Loader=yaml.Loader)
    assert (
        loaded_dict["_class"] == obj.__class__
    ), "object class does not match loaded class"
    for k in loaded_dict.keys():
        if k != "directory":
            obj.__dict__[k] = loaded_dict[k]


def load_object(filepath):
    """
    reads a python object from a yaml config
    """
    if not os.path.exists(filepath):
        return None
    else:
        config = open(filepath).read()
        loaded_dict = yaml.load(config, Loader=yaml.Loader)
        klass = loaded_dict["_class"]
        s = inspect.signature(klass.__init__)
        init_args = list(s.parameters.keys())
        init_args = [arg for arg in init_args if arg != "self"]
        kwargs = {
            arg: loaded_dict[arg] for arg in init_args if arg in loaded_dict.keys()
        }
        obj = klass(**kwargs)
        for k in loaded_dict.keys():
            obj.__dict__[k] = loaded_dict[k]

        sep = os.path.sep
        if sep not in filepath:
            sep = os.path.altsep
        assert sep in filepath, "Directory must contain '\\' or '/'"

        directory = os.path.join(*filepath.split(sep)[:-1])
        obj.directory = directory
        return obj


def clean_variable(var):
    if type(var) is dict:
        return {clean_variable(k): clean_variable(var[k]) for k in var.keys()}
    if type(var) is list:
        return [clean_variable(v) for v in var]
    try:
        if np.isfinite(var):
            if type(var) is int:
                return int(var)
            else:
                return float(var)
    except Exception:
        return var


def save_object(obj, filepath):
    d = obj.__dict__.copy()
    d["_class"] = obj.__class__
    d["_saved_on"] = time.ctime()
    omit_keys = ["directory", "logger"]
    for k in omit_keys:
        if k in d.keys():
            del d[k]
    for k in list(d.keys()):
        try:
            pickle.dumps(d[k])
            d[k] = clean_variable(d[k])
        except Exception:
            d.pop(k)
    with open(filepath, "w+") as f:
        f.write(yaml.dump(d))


def save_experiment(exp):
    if exp.device is not None:
        exp.device.save()
    for culture in exp.cultures.values():
        if culture is not None:
            culture.save()


def load_experiment(exp):
    directory = exp.directory
    if not os.path.exists(directory):
        os.mkdir(directory)
        print("Created new experiment directory: %s" % directory)
    else:
        print("Experiment directory: '%s'" % directory)
        # t0 = time.time()
        device_config_path = os.path.join(directory, "device_config.yaml")
        if os.path.exists(device_config_path):
            exp.device = load_object(filepath=device_config_path)
            exp.device.load()  # load cultures
        else:
            print("No device config found.")
