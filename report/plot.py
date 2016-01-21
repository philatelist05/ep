#!/usr/bin/python

from matplotlib import pyplot as plt
import csv
import os
import copy
import numpy as np
from matplotlib import rc


BLACKLIST = ['time', 'i', 'tag', 'branches_percent', 'branch-misses_percent', 'L1-dcache-load-misses_percent', 'instructions_percent', 'L1-dcache-loads_percent', 'cycles_percent']


def plot_lines(xs, values, labels, names):
    (filename, xname, yname, title) = names
    with plt.style.context('fivethirtyeight'):
        plt.figure(frameon=True, figsize=(14, 9))
        ax = plt.gca()
        ax.get_yaxis().get_major_formatter().set_scientific(False)
        print xs
        print labels
        lines = ()
        for ys in values:
            print ys
            lines += tuple(plt.plot(range(len(ys)), ys))
        plt.xticks(range(len(xs)), xs)
        plt.legend(lines, tuple(labels))
        plt.xlabel(xname)
        plt.ylabel(yname)
        plt.title(title)
        plt.tight_layout()
        plt.autoscale()
        plt.savefig(filename + '.png')


def calc_stats(data):
    for t in data.keys():
        tagraw = data[t]
        for k in tagraw.keys():
            npdata = np.array(tagraw[k])
            tagraw[k + '-mean'] = np.mean(npdata)
            tagraw[k + '-median'] = np.median(npdata)
            tagraw[k + '-std'] = np.std(npdata)
    return data


def convert(to_convert):
    result = None
    try:
        result = int(to_convert)
    except ValueError:
        pass
    try:
        result = float(to_convert)
    except ValueError:
        pass
    return result


def plot(tags, labels, filename, title, ylabel='Count'):
    ys = [[] for i in range(len(labels))]
    for t in tags:
        for i, v in enumerate(labels):
            ys[i].append(data[t][v])
    plot_lines(tags, ys, labels, (filename, 'Version', ylabel, title))


data = {}
for root, dirs, files in os.walk('results/'):
    for f in files:
        print 'Reading ' + f
        with open('results/' + f, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=';')
            keys = copy.deepcopy(reader.fieldnames)
            for k in BLACKLIST:
                keys.remove(k)
            for row in reader:
                tag = row['tag']
                if tag is None or len(tag) == 0:
                    print 'skipping row with empty tag'
                    continue
                if tag not in data.keys():
                    data[tag] = {}
                    for k in keys:
                        data[tag][k] = []
                for k in keys:
                    converted = convert(row[k])
                    if converted is not None:
                        data[tag][k].append(converted)

data = calc_stats(data)

tags = data.keys()
tags.sort(key=lambda item: (len(item), item[1:]))

labels = ['instructions-mean', 'cycles-mean']
plot(tags, labels, 'ins_cycles', 'Instructions and cycles')

labels = ['branches-mean', 'branch-misses-mean']
plot(tags, labels, 'branches', 'Branches and misses')

labels = ['L1-dcache-loads-mean', 'L1-dcache-loads-misses-mean']
plot(tags, labels, 'cache', 'L1 cache loads and misses')

labels = ['seconds-mean']
plot(tags, labels, 'seconds', 'Runtime in seconds', 'seconds')

labels = ['instructions-mean', 'cycles-mean', 'branches-mean', 'branch-misses-mean', 'L1-dcache-loads-mean', 'L1-dcache-loads-misses-mean']
labels = ['instructions-mean', 'cycles-mean', 'branches-mean', 'branch-misses-mean', 'L1-dcache-loads-mean']
plot(tags, labels, 'summary', 'Summary')
