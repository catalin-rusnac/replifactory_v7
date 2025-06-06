import os
import time


def read_file_tail(filepath, lines=1000, _buffer=4096):
    lines = int(lines)
    with open(filepath, "rb") as f:
        # place holder for the lines found
        lines_found = []

        # block counter will be multiplied by buffer
        # to get the block size from the end
        block_counter = -1

        # loop until we find X lines
        while len(lines_found) < lines + 1:
            try:
                f.seek(block_counter * _buffer, os.SEEK_END)
            except IOError:  # either file is too small, or too many lines requested
                f.seek(0)
                lines_found = f.readlines()
                break
            lines_found = f.readlines()
            # we found enough lines, get out
            # decrement the block counter to get the
            # next X bytes
            block_counter -= 1
    return lines_found


# def read_csv_tail(filepath, lines=1000, _buffer=4096):
#     """Tail a file and get X lines from the end
#     modified from https://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-similar-to-tail/136368#136368
#     """
#     header = open(filepath).readline().rstrip().split(",")
#     lines_found = read_file_tail(filepath=filepath, lines=lines, _buffer=_buffer)
#
#     lines_found = lines_found[1:]  # cut header if lines > total lines in file
#     lines_found = lines_found[-lines:]
#     lines_found = [
#         line.decode().rstrip().replace(" ", "").split(",") for line in lines_found
#     ]
#     lines_found = np.array(lines_found)
#     data = lines_found[:, 1:]
#     d = []
#     for data_line in data:
#         try:
#             d += [pd.to_numeric(data_line)]
#         except ValueError:
#             line = []
#             for value in data_line:
#                 try:
#                     line += [pd.to_numeric(value)]
#                 except ValueError:
#                     line += [np.nan]
#             d += line
#     data = d
#
#     data = [pd.to_numeric(data_line) for data_line in data]
#     timestamp = lines_found[:, 0]
#
#     df = pd.DataFrame(data, columns=header[1:])
#
#     try:
#         timestamp = pd.to_numeric(timestamp)  # 5 ms  for 10 000 lines
#     except ValueError:
#         timestamp = pd.to_datetime(timestamp)  # 1.3 seconds for 10 000 lines
#         timestamp = pd.to_numeric(timestamp)
#
#     df.index = timestamp
#
#     df.index.name = header[0]
#     return df


class CultureDict(dict):
    def __init__(self, device):
        super().__init__()
        self.device = device

    def __setitem__(self, vial, c):
        if c is not None:
            assert os.path.exists(
                self.device.directory
            ), "device directory does not exist:"
            new_culture_directory = os.path.join(
                self.device.directory, "vial_%d" % vial
            )

            existing_config = os.path.join(new_culture_directory, "culture_config.yaml")
            if c.directory is None and os.path.exists(existing_config):
                raise RuntimeError("Culture %d config exists" % vial)
            if not os.path.exists(new_culture_directory):
                os.mkdir(new_culture_directory)
            c.vial_number = vial
            # c.experiment_directory = self.device.directory
            c.directory = new_culture_directory
            c.device = self.device

        super().__setitem__(vial, c)


def write_variable(culture, variable_name, value):
    filepath = os.path.join(culture.directory, "%s.csv" % variable_name)
    if not os.path.exists(filepath):
        with open(filepath, "w+") as f:
            f.write("time,%s\n" % variable_name)
    with open(filepath, "a") as f:
        data_string = "%.1f, %.5f\n" % (int(time.time()), value)
        f.write(data_string)

    # # save variable value to sql lite database
    culture.sql_db.add_variable(variable_name, value)

# initialize sql lite database storing culture parameters and the following variables: experiment state, culture name, species, od, concentration
def init_sql_db(culture):
    import sqlite3
    import os

    db_path = os.path.join(culture.directory, "culture_parameters.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS culture_parameters (
            culture_name text,
            species text,
            od real,
            concentration real
            )"""
    )
    conn.commit()
    return conn




class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
