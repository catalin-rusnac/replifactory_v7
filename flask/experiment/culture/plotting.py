import os
import time

import ipywidgets as widgets
import matplotlib.pyplot as plt
import numpy as np
from IPython.core.display import clear_output
from ipywidgets import HBox, Layout, VBox

from replifactory.util.growth_rate import adaptive_window_doubling_time
from replifactory.util.other import read_csv_tail


class Plotter:
    def __init__(self, culture, last_hours=48):
        self.culture = culture
        self.dilution_timepoints = None
        self.dose_values = None
        self.t_min = 0
        self.last_hours = last_hours

    # def build_figure(self):
    #     self.fig, self.ax = plt.subplots(figsize=[16, 8], dpi=100)
    #     ax.set_xlabel("Time [hours]")

    #     self.update_df()
    #     self.update_time2()
    #     self.plot_od()
    #     self.plot_dose()
    #     self.plot_generations()

    def update_od(self):
        last_hours = self.last_hours
        culture = self.culture
        od_filepath = os.path.join(culture.directory, "od.csv")
        df = read_csv_tail(filepath=od_filepath, lines=last_hours * 60)
        self.t_min = df.index.values[-1] - last_hours * 3600
        self.df = df[df.index >= self.t_min]

    def load_pumps(self):
        pass

    def update_df(self):
        if not hasattr(self, "df"):
            self.update_od()

        for filename in ["log2_dilution_coefficient.csv", "medium2_concentration.csv"]:
            filepath = os.path.join(self.culture.directory, filename)
            if os.path.exists(filepath):
                df = read_csv_tail(filepath, lines=50 + last_hours * 60)
                df = df[df.index >= self.t_min]
                self.df = self.df.append(df)

    def plot_od(self):
        od = np.array(self.df.od)
        t = self.df.index
        ax = self.ax
        ax.plot(t / 3600, od, "k.", label="Optical Density")
        ax.set_ylabel("Optical Density")

    def plot_dose(self):
        ax3 = self.fig.axes[0].twinx()
        dosevalues = self.df.medium2_concentration[
            ~self.df.medium2_concentration.isna()
        ]
        tdose = dosevalues.index
        ax3.step(tdose / 3600, dosevalues, "r^-", where="post", label="dose")
        # dose0 = dosevalues.values[0]
        # dose0_t = tdose[0]

        ax3.spines["left"].set_position(("axes", -0.1))
        ax3.yaxis.set_label_position("left")
        ax3.yaxis.set_ticks_position("left")
        ax3.yaxis.set_tick_params(color="r")
        ax3.set_ylabel("Dose [mM]", color="r")
        ax3.grid(color="r", linestyle=":", alpha=0.5)

    def plot_generations(self):
        try:
            ax4 = self.ax.twinx()
            ax4.plot()
            df = self.df.log2_dilution_coefficient[
                ~self.df.log2_dilution_coefficient.isna()
            ]
            ax4.plot(
                df.index / 3600,
                df.values,
                ".--",
                color="g",
                label="generation [log2(dilution coefficient)]",
            )
            ax4.yaxis.set_tick_params(color="g")
            ax4.spines["right"].set_position(("axes", 1.05))
            ax4.grid(color="g", linestyle="-.", alpha=0.5)
            ax4.set_ylabel("Generation number", color="g")
        except Exception:
            pass

    def update_time2(self):
        self.df.loc[:, "time2"] = self.df.index / 3600
        self.df.time2 = self.df.time2 - min(self.df.time2)
        # if now-t[-1]<3600*24:
        #     ax.axvline(now,linestyle="-",linewidth=1,color="pink",label="now (%s)"%time.ctime()[4:-5])
        # ax.set_ylim(-0.05, 1.6)

    # def plot_growth_rate(self):
    #     ax2 = self.ax.twinx()
    #     #
    #     td_timepoints, td, tderr = adaptive_window_doubling_time(t, od, dilution_timepoints=dilution_timepoints)

    #     markers, caps, bars = ax2.errorbar(td_timepoints / 3600, td, tderr,
    #                                        alpha=0.5, label="doubling time")
    #     [bar.set_alpha(0.1) for bar in bars]
    #     try:
    #         td = np.array(td)
    #         tderr = np.array(tderr)
    #         tdmax = np.nanmax(td[tderr < 0.05])
    #         tdmin = np.nanmin(td[tderr < 0.05])
    #         ax2.set_ylim(tdmin * 0.5, tdmax * 1.2)
    #     except Exception:
    #         pass
    #     ax2.grid(color="xkcd:light blue", linestyle=":", alpha=0.8)
    #     ax2.yaxis.set_tick_params(color="xkcd:cerulean")
    #     ax2.set_ylabel("Doubling time [hours]", color="xkcd:cerulean")

    # def cleanup(self):
    #     handles, labels = [], []
    #     for axis in fig.axes:
    #         handle, label = axis.get_legend_handles_labels()
    #         axis.legend([])
    #         handles += handle
    #         labels += label
    #     ax.legend(handles, labels, loc=2)

    #     xticks = ax.get_xticks()
    #     for axis in fig.axes:
    #         axis.set_xticks(xticks)

    #     tmin = xticks[0]
    #     xtick_labels = [round(t - tmin, 2) for t in xticks]
    #     # fig.axes[1].set_ylim(0.1, 10)
    #     ax.set_xticklabels(xtick_labels)
    #     # fig.axes[1].set_yticks([])

    #     ax.set_yscale("log")
    #     od_ticks = [0.001, 0.01, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 1]
    #     ax.set_yticks(od_ticks)
    #     ax.set_yticklabels(od_ticks)
    #     ax.set_ylim(0.0008, 1.6)
    #     ax.grid(color="k", linestyle="--", alpha=0.3)
    #     ax.set_xlabel("Time [hours from %s]" % time.ctime(tmin * 3600))

    #     plot_title = "%s %s" % (culture.name, culture.directory)
    #     fig.axes[0].set_title(plot_title)


def plot_culture(culture, last_hours=24, plot_growth_rate=False):
    od_filepath = os.path.join(culture.directory, "od.csv")
    df = read_csv_tail(filepath=od_filepath, lines=last_hours * 60)
    t = df.index.values
    od = df.values.ravel()
    t_min = t[-1] - last_hours * 3600
    odw = od[t > t_min]
    tw = t[t > t_min]
    drug_concentration_file = os.path.join(
        culture.directory, "medium2_concentration.csv"
    )
    tdose = None
    dosevalues = None
    if os.path.exists(drug_concentration_file):
        dosedf = read_csv_tail(drug_concentration_file, lines=50 + last_hours * 10)
        tdose = dosedf.index.values
        dosevalues = dosedf.values.ravel()[tdose > t_min]
        tdose = tdose[tdose > t_min]

    # fig = plot_gr(tw, odw, tdose)

    # plot growth rate
    od_values = odw
    time_values = tw
    dilution_timepoints = tdose
    od = np.array(od_values)
    t = np.array(time_values)

    fig, ax = plt.subplots(figsize=[16, 8], dpi=100)
    # i = 0
    # lines = []
    ax.plot(t / 3600, od, "k.", label="Optical Density")
    # now = time.time()
    # if now-t[-1]<3600*24:
    #     ax.axvline(now,linestyle="-",linewidth=1,color="pink",label="now (%s)"%time.ctime()[4:-5])
    # ax.set_ylim(-0.05, 1.6)

    od[od <= 0] = 1e-6
    ax.set_ylabel("Optical Density")
    ax.set_xlabel("Time [hours]")

    # Growth rate
    if plot_growth_rate:
        ax2 = ax.twinx()
        #
        td_timepoints, td, tderr = adaptive_window_doubling_time(
            t, od, dilution_timepoints=dilution_timepoints
        )

        markers, caps, bars = ax2.errorbar(
            td_timepoints / 3600, td, tderr, alpha=0.5, label="doubling time"
        )
        [bar.set_alpha(0.1) for bar in bars]
        try:
            td = np.array(td)
            tderr = np.array(tderr)
            tdmax = np.nanmax(td[tderr < 0.05])
            tdmin = np.nanmin(td[tderr < 0.05])
            ax2.set_ylim(tdmin * 0.5, tdmax * 1.2)
        except Exception:
            pass
        ax2.grid(color="xkcd:light blue", linestyle=":", alpha=0.8)
        ax2.yaxis.set_tick_params(color="xkcd:cerulean")
        ax2.set_ylabel("Doubling time [hours]", color="xkcd:cerulean")

    if tdose is not None:
        ax3 = fig.axes[0].twinx()
        ax3.step(tdose / 3600, dosevalues, "r^-", where="post", label="dose")
        ax3.spines["left"].set_position(("axes", -0.1))
        ax3.yaxis.set_label_position("left")
        ax3.yaxis.set_ticks_position("left")
        ax3.yaxis.set_tick_params(color="r")
        ax3.set_ylabel("Dose [mM]", color="r")
        ax3.grid(color="r", linestyle=":", alpha=0.5)
    try:
        df = read_csv_tail(
            os.path.join(culture.directory, "log2_dilution_coefficient.csv"), lines=1440
        )  # 24h
        df.index = df.index / 3600
        ax4 = ax.twinx()
        df.log2_dilution_coefficient.plot(
            style=".--",
            color="g",
            label="generation [log2(dilution coefficient)]",
            axes=ax4,
        )
        ax4.yaxis.set_tick_params(color="g")
        ax4.spines["right"].set_position(("axes", 1.05))
        ax4.grid(color="g", linestyle="-.", alpha=0.5)

        ax4.set_ylabel("Generation number", color="g")
    except Exception:
        pass
    handles, labels = [], []
    for axis in fig.axes:
        handle, label = axis.get_legend_handles_labels()
        axis.legend([])
        handles += handle
        labels += label
    ax.legend(handles, labels, loc=2)

    xticks = ax.get_xticks()
    for axis in fig.axes:
        axis.set_xticks(xticks)

    tmin = xticks[0]
    xtick_labels = [round(t - tmin, 2) for t in xticks]
    # fig.axes[1].set_ylim(0.1, 10)
    ax.set_xticklabels(xtick_labels)
    # fig.axes[1].set_yticks([])

    ax.set_yscale("log")
    od_ticks = [0.001, 0.01, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 1]
    ax.set_yticks(od_ticks)
    ax.set_yticklabels(od_ticks)
    ax.set_ylim(0.0008, 1.6)
    ax.grid(color="k", linestyle="--", alpha=0.3)
    ax.set_xlabel("Time [hours from %s]" % time.ctime(tmin * 3600))

    plot_title = "%s %s" % (culture.name, culture.directory)
    fig.axes[0].set_title(plot_title)
    return fig


def plot_temperature(culture, fig, last_hours):
    df = read_csv_tail(
        os.path.join(culture.device.directory, "temperature.csv"), last_hours * 60
    )
    ax4 = fig.axes[0].twinx()
    ax4.plot(df.index.values / 3600, df.temperature_vials, ".", label="temperature")
    ax4.spines["right"].set_position(("axes", 0.1))
    ax4.yaxis.set_label_position("right")
    ax4.yaxis.set_ticks_position("right")
    ax4.legend()


last_hours = 24
vials_list = range(1, 8)


class CommonPlotterWidget:
    def __init__(self, main_gui):
        self.main_gui = main_gui
        self.plot_button = widgets.Button(description="plot")
        self.plot_button.on_click(self.handle_plot_button)
        self.output = widgets.Output(layout=Layout(width="1200px"))
        self.checkboxes = [
            widgets.Checkbox(
                description="Vial %d" % v,
                indent=False,
                layout=Layout(width="140px"),
                value=True,
            )
            for v in range(1, 8)
        ]
        self.last_hours = widgets.IntText(
            description="time window",
            description_tooltip="hours before the last OD measurement",
            value=24,
            style={"description_width": "80px"},
            layout=Layout(width="135px"),
        )
        self.selector = HBox(self.checkboxes, layout=Layout(width="500px"))
        self.header = HBox([self.plot_button, self.last_hours, self.selector])
        acc = widgets.Accordion()
        acc.children = [VBox([self.header, self.output])]
        acc.set_title(0, "Common plot")
        self.widget = acc

    def handle_plot_button(self, button):
        with self.output:
            clear_output()
            try:
                self.plot_button.disabled = True
                self.plot_button.description = "plotting..."
                vials_list = [
                    int(w.description[-1]) for w in self.checkboxes if w.value
                ]
                last_hours = self.last_hours.value
                self.common_plot(vials_list=vials_list, last_hours=last_hours)
            finally:
                self.plot_button.disabled = False
                self.plot_button.description = "plot"

    def common_plot(self, vials_list=[1, 2, 3, 4, 5, 6, 7], last_hours=24):
        dev = self.main_gui.device
        fig, ax = plt.subplots(figsize=[12, 6], dpi=100)
        ax3 = fig.axes[0].twinx()
        ax4 = ax.twinx()

        colors = {
            1: "tab:blue",
            2: "tab:orange",
            3: "tab:green",
            4: "tab:red",
            5: "tab:purple",
            6: "tab:brown",
            7: "tab:pink",
        }

        for v in vials_list:
            culture = dev.cultures[v]
            od_filepath = os.path.join(culture.directory, "od.csv")
            df = read_csv_tail(filepath=od_filepath, lines=last_hours * 60)
            t = df.index.values
            od = df.values.ravel()
            t_min = t[-1] - last_hours * 3600
            odw = od[t > t_min]
            tw = t[t > t_min]
            drug_concentration_file = os.path.join(
                culture.directory, "medium2_concentration.csv"
            )
            tdose = None
            dosevalues = None
            if os.path.exists(drug_concentration_file):
                dosedf = read_csv_tail(
                    drug_concentration_file, lines=50 + last_hours * 10
                )
                tdose = dosedf.index.values
                dosevalues = dosedf.values.ravel()[tdose > t_min]
                tdose = tdose[tdose > t_min]

            if tdose is not None:
                if len(tdose) > 0:
                    ax3.step(
                        tdose / 3600,
                        dosevalues,
                        "^-.",
                        color=colors[v],
                        alpha=0.6,
                        label="Vial %d dose" % v,
                        where="post",
                    )

            # plot growth rate
            od_values = odw
            time_values = tw
            # dilution_timepoints = tdose
            od = np.array(od_values)
            t = np.array(time_values)

            # i = 0
            # lines = []
            if len(od) > 0:
                ax.plot(
                    t / 3600,
                    od,
                    ".:",
                    color=colors[v],
                    markersize=3,
                    label="Vial %d OD" % v,
                )

                # if now-t[-1]<3600*24:
                #     ax.axvline(now,linestyle="-",linewidth=1,color="pink",label="now (%s)"%time.ctime()[4:-5])
                # ax.set_ylim(-0.05, 1.6)

                od[od <= 0] = 1e-6
                ax.set_ylabel("Optical Density")
                ax.set_xlabel("Time [hours]")

            gen_file = os.path.join(culture.directory, "log2_dilution_coefficient.csv")

            if os.path.exists(gen_file):
                df = read_csv_tail(gen_file, lines=last_hours * 60)  # 24h
                df = df[df.index > t_min]
                if df.shape[0] > 0:
                    df.index = df.index / 3600
                    df.log2_dilution_coefficient.plot(
                        style="--",
                        marker="s",
                        color=colors[v],
                        alpha=0.3,
                        label="Vial %d generation" % culture.vial_number,
                        axes=ax4,
                    )

            handles, labels = [], []
            for axis in fig.axes:
                handle, label = axis.get_legend_handles_labels()
                axis.legend([])
                handles += handle
                labels += label
            ax.legend(handles, labels, loc=2)

            xticks = ax.get_xticks()
            for axis in fig.axes:
                axis.set_xticks(xticks)

            tmin = xticks[0]
            xtick_labels = [round(t - tmin, 2) for t in xticks]
            # fig.axes[1].set_ylim(0.1, 10)
            ax.set_xticklabels(xtick_labels)
            # fig.axes[1].set_yticks([])

            ax.set_yscale("log")
            od_ticks = [0.001, 0.01, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 1]
            ax.set_yticks(od_ticks)
            ax.set_yticklabels(od_ticks)
            ax.set_ylim(0.0008, 1.6)
            ax.grid(color="k", linestyle="--", alpha=0.3)
            ax.set_xlabel("Time [hours from %s]" % time.ctime(tmin * 3600))
        ax3.spines["left"].set_position(("axes", -0.08))
        ax3.yaxis.set_label_position("left")
        ax3.yaxis.set_ticks_position("left")
        ax3.yaxis.set_tick_params(color="r")
        ax3.set_ylabel("Dose [mM]", color="r")
        ax3.grid(color="r", linestyle=":", alpha=0.5)

        ax4.yaxis.set_tick_params(color="g")
        ax4.spines["right"].set_position(("axes", 1))
        ax4.grid(color="g", linestyle="-.", alpha=0.5)
        ax4.set_ylabel("Generation number", color="g")

        plot_title = os.path.abspath(dev.directory)
        fig.axes[0].set_title(plot_title)
        plt.show()
