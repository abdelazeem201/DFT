# -*- coding: utf-8 -*-

import utils
import config
import argparse
import math
import os
import matplotlib.pyplot as plt
import seaborn as sns
import re
import numpy as np
import pandas as pd
from circuit import Circuit
from pfs import PFS
import observation as obsv
import pdb

colors = ["green", "red", "blue", "orange", "purple", "black"]


def pars_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-ckt", type=str, required=False,
                        help="ckt file address")
    parser.add_argument("-v", type=str, required=False,
                        help="verilog file address")
    parser.add_argument("-synv", type=str, required=False, help="syn ver")
    parser.add_argument("-tp", type=int, required=False,
                        help="tp count for random sim")
    parser.add_argument("-fault", type=int, required=False, help="fault count")
    parser.add_argument("-code", type=str, required=False,
                        help="code for general use")
    parser.add_argument("-tpLoad", type=int, required=False,
                        help="tp count for loading STAFAN")
    parser.add_argument("-cpu", type=int, required=False,
                        help="number of parallel CPUs")
    parser.add_argument("-func", type=str, required=False,
                        help="What operation you want to run")
    parser.add_argument("-OPIalg", type=str,
                        required=False, help="OPI Algorithm")
    parser.add_argument("-Bth", type=float, required=False, default=0.1,
                        help="Obsv. threshold for OPI candidate selection")
    parser.add_argument("-HTO_th", type=float, required=False, default=None,
                        help="Obsv. threshold for OPI candidate selection")
    parser.add_argument("-HTC_th", type=float, required=False, default=None,
                        help="Ctrl. threshold for OPI candidate selection")
    parser.add_argument("-opCount", type=int, required=False,
                        default=None, help="OP count")
    parser.add_argument("-op_fname", type=str, required=False,
                        default=None, help="OP file name")
    parser.add_argument("-TPI_num", type=int, required=False, default=None,
                        help="Number of TPI candidates specified")
    parser.add_argument("-times", type=int, required=False,
                        help="Repetition count for figures")
    parser.add_argument("-ci", type=int, required=False,
                        help="Confidence value (mu/std)")
    args = parser.parse_args()

    return args


def read_circuit(args):
    circuit = None
    if args.ckt:
        circuit = Circuit(args.ckt)

    elif args.v:
        circuit = Circuit(args.v)
    return circuit


def node_info(node):

    node_parameters = {}
    node_parameters["C0"] = node.C0
    node_parameters["C1"] = node.C1
    node_parameters["S"] = node.S
    node_parameters["B0"] = node.B0
    node_parameters["B1"] = node.B1
    node_parameters["CB0"] = node.CB0
    node_parameters["CB1"] = node.CB1
    node_parameters["B"] = node.B

    return node_parameters


def tpfc_stafan(circuit, times=1, tp=100, tpLoad=100):
    """
    Fault coverage estimation
    STAFAN measures are calculates many times with constant tpLoad count of test patterns.
    Then, the fault coverage is calculated using STAFAN values and the given tp.
    """
    df = pd.DataFrame(columns=["tp", "fc", "batch"])
    for i in range(times):
        path = f"{config.STAFAN_DIR}/{circuit.c_name}"
        if not os.path.exists(path):
            os.makedirs(path)
        fname = f"{path}/{circuit.c_name}-TP{tpLoad}-{i}.stafan"
        if not os.path.exists(fname):
            circuit.STAFAN(tpLoad)
            circuit.save_TMs(tp=tpLoad, fname=fname)
        else:
            circuit.load_TMs(fname)

        for tpc in range(1, tp+1):
            try:
                row = {"tp": tpc, "fc": circuit.STAFAN_FC(tpc)*100, "batch": i}
                df = df.append(row, ignore_index=True)
            except:
                continue

    plot = sns.lineplot(x=df["tp"], y=df["fc"],
                        color="green", ci=99.99, label='STAFAN (constant tpLoad)')

    plt.xlim(50, tp)
    plot.set_ylabel(f"Fault Coverage(FC%)", fontsize=13)
    plot.set_xlabel("Test Pattern Count #TP", fontsize=13)
    plot.set_title(
        f"Dependency of fault coverage on random test patterns\n\
        for circuit {circuit.c_name}\n \
        method: STAFAN (constant tpLoad) ", fontsize=13)

    path = f"{config.FIG_DIR}/{circuit.c_name}/fc-estimation/"
    if not os.path.exists(path):
        os.makedirs(path)

    fname = path+f"tpfc-stafan-constant-{circuit.c_name}-TP{tp}.png"
    plt.tight_layout()
    plt.savefig(fname)
    print(f"Figure saved in {fname}")
    return plot


def diff_tp_stafan(circuit):
    """
    Fault coverage estimation
    STAFAN measures are calculates many times with different tpLoad count of test patterns.
    Then, the fault coverage is calculated using STAFAN values with the correspoing tp count.
    TODO: list of tps should be generated automatically according to ?
    """
    tps = [100, 200, 500,
           1000, 2000, 5000,
           10_000, 20_000, 50_000,
           100_000, 200_000, 500_000,
           1_000_000, 10_000_000]

    set = 0
    tp_size = [f"{tp}-{set}" for tp in tps[-2]]+["1000000", "10000000"]
    for i in tp_size:
        path = f"{config.STAFAN_DIR}/{circuit.c_name}"
        if not os.path.exists(path):
            os.makedirs(path)
        fname = f"{path}/{circuit.c_name}-TP{i}.stafan"
        if not os.path.exists(fname):
            tpc = re.findall(r"\d+", i)[0]
            circuit.STAFAN(int(tpc))
            circuit.save_TMs(tp=tp_size, fname=fname)
        else:
            circuit.load_TMs(fname)

        fc_sequence = [0]
        tp_sequence = [0]
        for tps in tp_size:
            tp = re.findall(r"\d+", i)[0]
            try:
                fc_sequence.append(circuit.STAFAN_FC(tps)*100)
                tp_sequence.append(tps)
            except:
                continue

        plot = sns.lineplot(x=tp_sequence, y=fc_sequence,
                            color="green", alpha=0.5)

    plot.set_ylabel(f"Fault Coverage (FC%)", fontsize=13)
    plot.set_xlabel("Test Pattern Count #TP", fontsize=13)
    plot.set_title(
        f"Dependency of fault coverage on random test patterns\n\
        for circuit {circuit.c_name}\n \
        method: STAFAN (different tpLoads)", fontsize=13)

    path = f"{config.FIG_DIR}/{circuit.c_name}/estimation-diff-tploads/"
    if not os.path.exists(path):
        os.makedirs(path)

    fname = path+f"tpfc-stafan-diff-tpload-{circuit.cname}.png"
    plt.tight_layout()
    plt.savefig(fname)


def tpfc_pfs(circuit, tp, times):
    """ Run and plot the TPFC figure by doing real fault simulation (PFS) 
        if times > 1, then the fault simulation is done several times with different sets of 
        random test patterns. The figure will show the range and the mean of FC value 
        through all simulations. 

        Parameters:
        -----------
        tp : int 
            number of patterns used for fault simulation 
        times : int 
            number of times fault simulation is done
    """

    df = pd.DataFrame(columns=["tp", "fc", "batch"])

    for batch in range(times):
        pfs = PFS(circuit)
        pfs.fault_list.add_all(circuit)
        fc = pfs.tpfc(tp, fault_drop=1)
        arr = [list(range(1, tp+1)), fc, [batch]*tp]
        df = df.append(pd.DataFrame(np.array(arr).T, columns=["tp", "fc", "batch"]),
                       ignore_index=True)
    plt.xlim(50, tp)
    plt.ylim(min(df[df["tp"] == 50]["fc"].tolist()), 100)
    # print(min(df[df["tp"]==50]["fc"].tolist()))
    # df["nfc"] = 100.00001 - df["fc"]
    plot = sns.lineplot(x=df["tp"], y=df["fc"], alpha=0.8,
                        color="b", ci=99.99, label="PFS")
    plot.set_ylabel(f"Fault Coverage", fontsize=13)
    plot.set_xlabel("Test Pattern Count #TP", fontsize=13)
    plot.set_title(f"Dependency of fault coverage on\n \
            random test patterns for {circuit.c_name}", fontsize=13)

    path = f"results/figures/"
    if not os.path.exists(path):
        os.makedirs(path)
    fname = path + f"tpfc-pfs-{circuit.c_name}-TP{tp}-times{times}.png"
    print(f"Figure saved in {fname}")
    plt.tight_layout()
    plt.savefig(fname)

    return plot


def tpfc_ppsf(circuit, ci, cpu, tp):
    """
    Fault simulation estimation using PPSF method with different sizes of tpLoads
    """
    path = os.path.join(config.FAULT_SIM_DIR, circuit.c_name)
    fname = os.path.join(path, "{}-ppsf-steps-ci{}-cpu{}.ppsf".format(
        circuit.c_name, ci, cpu))
    p_init = utils.load_pd_ppsf_conf(fname)
    tps = np.arange(0, tp+1, 10)
    fcs = []
    for tp in tps:
        # fc is estimated based on constant count of tps for ppsf
        fcs.append(utils.estimate_FC(p_init, tp=tp)*100)
    plot = sns.lineplot(x=tps, y=fcs, color="red", label="PPSF")
    plt.xlim(50, tp)
    plot.set_ylabel(f"Fault Coverage (FC%)", fontsize=13)
    plot.set_xlabel("Test Pattern Count #TP", fontsize=13)
    plot.set_title(
        f"fault coverage for random test patterns\n\
        for circuit {circuit.c_name} \n \
        method: PPSF", fontsize=13)

    # path = f"./results/figures"
    path = f"{config.FIG_DIR}/{circuit.c_name}/fc-estimation/"
    fname = f"{path}/tpfc-ppsf-{circuit.c_name}-CI{ci}-cpu{cpu}.png"
    print(f"Figure saved in {fname}")
    plt.tight_layout()
    plt.savefig(fname)
    return plot


def compare_stafan_ppsf_pfs(circuit, times, tp, tpLoad, ci, cpu):
    """
    compare fault coverage using STAFAN vs. PFS vs. PPSF.
    """

    plt1 = tpfc_stafan(circuit, times,
                       tpLoad=tpLoad, tp=tp)
    plt2 = tpfc_pfs(circuit, times=times, tp=tp)
    plt3 = tpfc_ppsf(circuit, ci=ci, cpu=cpu, tp=tp)

    plt.title(
        f"Dependency of fault coverage on\nrandom test patterns for {circuit.c_name}", fontsize=13)

    path = f"{config.FIG_DIR}/{circuit.c_name}/compare/"
    if not os.path.exists(path):
        os.makedirs(path)

    fname = path+f"tpfc-compare-stafan(constant)-pfs-ppsf-{circuit.c_name}.png"
    plt.tight_layout()
    plt.savefig(fname)
    print(f"\nFinal figure saved in {fname}.")


def ppsf_ci(circuit, cpu, _cis):
    i = 0
    for ci in _cis:
        path = os.path.join(config.FAULT_SIM_DIR, circuit.c_name)
        fname = os.path.join(
            path, f"{circuit.c_name}-ppsf-steps-ci{ci}-cpu{cpu}.ppsf")
        res_ppsf = utils.load_pd_ppsf_conf(fname)
        ppsf_pd = [x for x in res_ppsf.values()]
        bins = np.logspace(np.floor(np.log10(min(ppsf_pd))),
                           np.log10(max(ppsf_pd)), 20)
        sns.histplot(ppsf_pd, alpha=0.2, kde=True, bins=bins,
                     color=colors[i], label=f"CI={ci}")  # Some issue here
        i += 1

    plt.xscale("log")
    # plt.yscale("log")
    handles, labels = plt.gca().get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    plt.rcParams["patch.force_edgecolor"] = False
    plt.legend(by_label.values(), by_label.keys())
    plt.xlabel('PD using PPSF')
    plt.ylabel('Count of faults')
    plt.title(f"Detection probability histogram with PPSF\n\
        for circuit{circuit.c_name}")
    path = f"{config.FIG_DIR}/{circuit.c_name}/ppsf/"
    if not os.path.exists(path):
        os.makedirs(path)

    fname = path+f"ppsf-CI-{circuit.c_name}.png"
    plt.tight_layout()
    plt.savefig(fname)
    print(f"\nFigure saved in {fname}.")


def ppsf_corr_ci(circuit, cpu, _cis, heatmap=False):
    """
    Scatterplot for each CI comparing to the max CI
    """
    df = pd.DataFrame(columns=["fault"].extend(["ci"+str(x) for x in _cis]))
    cis = []
    for c in _cis:
        path = os.path.join(config.FAULT_SIM_DIR, circuit.c_name)
        fname = os.path.join(
            path, f"{circuit.c_name}-ppsf-steps-ci{c}-cpu{cpu}.ppsf")
        cis.append(utils.load_pd_ppsf_conf(fname))
    fault_list = [i for i in cis[0].keys()]
    for f in fault_list:
        row = {"fault": f}
        for idx, c in enumerate(_cis):
            row["ci" + str(c)] = cis[idx][f]
        try:
            df = df.append(row, ignore_index=True)
        except:
            pass

    max_ci = max(_cis)
    _cis.remove(max_ci)
    max_ci_col = "ci" + str(max_ci)

    subs = math.ceil(math.sqrt(len(_cis)))
    subs2 = subs
    if subs*(subs-1) == len(_cis):
        subs2 -= 1
    fig, ax = plt.subplots(subs2, subs, figsize=(4*subs, 4*subs2))

    for idx, c in enumerate(_cis):
        i = idx//subs
        j = idx % subs
        ax[i, j].set_yscale("log")
        ax[i, j].set_xscale("log")
        ax[i, j].set_aspect(1)
        col = "ci" + str(c)
        sns.scatterplot(x=df[max_ci_col], y=df[col],
                        color=colors[idx], alpha=0.3, s=6, ax=ax[i, j])
        ax[i, j].set_ylabel(f"PD (CI={c})")
        ax[i, j].set_xlabel(f"PD (CI={max_ci})")

    if heatmap:
        sns.heatmap(df.corr(), annot=True, fmt="f", cmap="YlGnBu")

    fig.suptitle("Mean of detection probability which are\n\
    in the given confidence interval.", fontsize=16)
    fig.tight_layout()
    fname = f"results/figures/ppsf-CIs-max{max_ci}-cpu{args.cpu}-{circuit.c_name}.png"
    plt.savefig(fname)
    print(f"Figure saved in {fname}")


def ppsf_error_ci(circuit, hist_scatter, cpu, _cis):
    """
    hist_scatter : str
        options: hist, scatter
    """
    df = pd.DataFrame(columns=["fault"].extend(["ci"+str(x) for x in _cis]))
    cis = []
    copy_cis = _cis.copy()
    for c in copy_cis:
        path = os.path.join(config.FAULT_SIM_DIR, circuit.c_name)
        fname = os.path.join(
            path, f"{circuit.c_name}-ppsf-steps-ci{c}-cpu{cpu}.ppsf")
        if not os.path.exists(fname):
            _cis.remove(c)
            continue
        cis.append(utils.load_pd_ppsf_conf(fname))
    fault_list = [i for i in cis[0].keys()]
    for f in fault_list:
        row = {"fault": f}
        for idx, c in enumerate(_cis):
            row["ci" + str(c)] = cis[idx][f]
        try:
            df = df.append(row, ignore_index=True)
        except:
            pass

    max_ci = max(_cis)
    _cis.remove(max_ci)
    max_ci_col = "ci" + str(max_ci)
    min_val = max(min((df["ci" + str(min(_cis))]-df[max_ci_col]) / df[max_ci_col]), -0.2)
    max_val = min(max((df["ci" + str(min(_cis))]-df[max_ci_col]) / df[max_ci_col]), 0.2)
    bins = np.linspace(min_val, max_val, 40)
    temp = []
    plt.rcParams["patch.force_edgecolor"] = False
    plt.figure(figsize=(12, 6))

    for idx, c in enumerate(_cis):
        col = "ci" + str(c)
        df[col+"_error"] = (df[col]-df[max_ci_col])/df[max_ci_col]
        temp.append(col+"_error")
        if hist_scatter == "hist":
            plt.xlim(min_val, max_val)  # TODO: Move me please --> why?
            sns.histplot(df[col+"_error"], alpha=0.1, color=colors[idx],
                         linewidth=0.01,
                         # line_kws=dict(edgecolor="white", linewidth=0.01),
                         kde=True,
                         label=col.replace("ci", "CI="), bins=bins)
            plt.legend()

        if hist_scatter == "scatter":
            sns.scatterplot(x=df[max_ci_col], y=df[col+"_error"],
                            color=colors[idx], alpha=0.5, s=8,
                            label=col.replace("ci", "CI="))

            plt.xscale("log")

    plt.title(f"Comparing error in detection probability (DP) value of faults measured with PPSF \n\
    for different confidence intervals (CIs) \n\
    CI = {max_ci} is used as the reference for error. \n\
    Number of parallel processes for PPSF = {cpu} \n\
    Circuit = {circuit.c_name}")
    if hist_scatter == "hist":
        plt.ylabel("Count of faults")
        plt.xlabel(f"Relative error to PPSF with CI={max_ci}")
    else:
        plt.ylabel(f"Relative error to PPSF with CI={max_ci}")
        plt.xlabel(f"PD using PPSF with CI={max_ci}")

    fname = f"results/figures/{circuit.c_name}-ppsf-error-CIs-{hist_scatter}plot-cpu{cpu}.png"
    plt.savefig(fname, bbox_inches="tight")
    print(f"Figure saved in {fname}")


def stafan_scoap(circuit):
    """STAFAN and SCOAP values"""
    # TODO: if matters, calculate the tps automatically according to the size of circuit
    circuit.SCOAP_CC()
    circuit.SCOAP_CO()

    tp_no = 10
    step = 2
    limit = 20_000
    node_num = 12
    mode = "*"  # + or *

    parameters = ["C0", "C1", "S", "B0", "B1", "CB0", "CB1", "B"]

    result_dict = {}
    for node in circuit.nodes_lev:
        for p in parameters:
            result_dict[(node, p)] = []

    tp_no_seq = []
    while tp_no < limit:
        # print(f"{tp_no = }") # TODO: why there is an error here?!
        fname = config.STAFAN_DIR + "/" + circuit.c_name + "/"
        if not os.path.exists(fname):
            os.makedirs(fname)
        fname += f"{circuit.c_name}-TP{tp_no}-0.stafan"
        if not os.path.exists(fname):
            circuit.STAFAN(tp_no, 8)
            circuit.save_TMs(fname)
        else:
            circuit.load_TMs(fname)

        tp_no_seq.append(tp_no)
        for node in circuit.nodes_lev:
            for p in parameters:
                result_dict[(node, p)].append(node_info(node)[p])
        if mode == "*":
            tp_no *= step
        elif mode == "+":
            tp_no += step
        else:
            raise "Operation is not valid"

    for param in parameters:
        test_array = result_dict[(circuit.nodes_lev[node_num], param)]
        sns.scatterplot(x=tp_no_seq, y=test_array)
        plot = sns.lineplot(x=tp_no_seq, y=test_array, label=param)
    ax = plt.gca()
    ax.grid(True, which="both")

    plot.set_ylabel("value")
    plot.set_xlabel("No. of tests")
    plot.set_title(
        f"SCOAP measures of node {node_num} in circuit {circuit.c_name}")
    # t.set_yscale("log")
    # t.set_xscale("log")

    path = f"{config.FIG_DIR}/{circuit.c_name}/stafan/"
    if not os.path.exists(path):
        os.makedirs(path)

    fname = path+f"{limit}-stafan.png"
    plt.tight_layout()
    plt.savefig(fname)


if __name__ == "__main__":
    args = pars_args()

    circuit = read_circuit(args)
    circuit.lev()

    ckt_name = args.ckt + "_" + args.synv if args.synv else args.ckt

    if args.func == "tpfc-stafan":
        tpfc_stafan(circuit=circuit, times=args.times,
                    tpLoad=args.tpLoad, tp=args.tp)

    elif args.func == "tpfc-pfs":
        tpfc_pfs(circuit=circuit, tp=args.tp, times=args.times)

    elif args.func == "tpfc-ppsf":
        tpfc_ppsf(circuit=circuit, ci=args.ci, cpu=args.cpu, tp=args.tp)

    elif args.func == "compare-tpfc":
        compare_stafan_ppsf_pfs(
            circuit=circuit, times=args.times, tp=args.tp, tpLoad=args.tpLoad, ci=args.ci, cpu=args.cpu)

    elif args.func == "diff-tp-stafan":
        diff_tp_stafan(circuit=circuit)

    elif args.func == "stafan":
        stafan_scoap(circuit=circuit)

    elif args.func == "ppsf-ci":
        ppsf_ci(circuit=circuit, cpu=args.cpu, _cis=[2, 3, 4])

    elif args.func == "ppsf-corr":
        ppsf_corr_ci(circuit=circuit, _cis=[1, 2, 3, 4, 5, 6, 10], cpu=args.cpu)

    elif args.func == "ppsf-error":
        ppsf_error_ci(circuit=circuit, hist_scatter="hist",cpu=args.cpu, _cis=[1, 2, 3, 4])
        # ppsf_error_ci(circuit=circuit, hist_scatter="scatter", cpu=args.cpu, _cis=[1, 2, 3, 4])

    else:
        raise ValueError(f"Function '{args.func}' does not exist.")

    # plt.show()