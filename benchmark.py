#!/usr/bin/python

import subprocess
import tempfile
import shutil
import os
import sys
import re
import datetime
import numbers

REMOTE = 'git@github.com:steff7/ep.git'
EXPECTED = '1ae56547f8865909'
EXPECTED_KEYS = [
     'tag',
     'instructions',
     'instructions_percent',
     'cycles',
     'cycles_percent',
     'branch-misses',
     'branch-misses_percent',
     'L1-dcache-loads',
     'L1-dcache-loads_percent',
     'L1-dcache-load-misses',
     'L1-dcache-load-misses_percent',
     'seconds']
ITERATIONS = 5
PIPEARGS = {'stdout': subprocess.PIPE, 'stderr': subprocess.PIPE}


def setup():
    print '-----------'
    print '   SETUP   '
    print '-----------'

    tagp = subprocess.Popen(['git', 'tag', '-l'], **PIPEARGS)
    (tagstring, err) = tagp.communicate()

    if len(err) > 0:
        print 'Encountered error while getting tag list, aborting.'
        print 'git error message:'
        print err
        quit()

    tags = tagstring.split()

    if len(tags) == 0:
        print 'Empty tag list, aborting'
        quit()

    tagpargs = ['git', 'status', '-uno', '--porcelain', '-z']
    tagp = subprocess.Popen(tagpargs, **PIPEARGS)
    (tagstring, err) = tagp.communicate()

    if len(err) > 0:
        print 'Encountered error while checking for modified master, aborting.'
        print 'git error message:'
        print err
        quit()

    if '\0' in tagstring:
        print 'Adding HEAD to tag list because working dir is unclean'
        tags += ['HEAD']

    if len(sys.argv) > 1:
        rfilename = sys.argv[1]
        rfile = open(rfilename, 'a')
        print 'Saving benchmark results to: ' + rfilename
    else:
        (rfd, rfilename) = tempfile.mkstemp()
        rfile = os.fdopen(rfd, 'a')
        print 'Created tempfile for benchmark results: ' + rfilename

    wd = tempfile.mkdtemp()
    print 'Cloning git repo to: ' + wd
    subprocess.check_call(['git', 'clone', REMOTE, wd], **PIPEARGS)
    os.chdir(wd)
    return (wd, (rfile, rfilename), tags)


def cleanup(wd, abort=True):
    print '-----------'
    print '  CLEANUP  '
    print '-----------'
    print 'Cleaning up'

    shutil.rmtree(wd)
    if abort:
        quit(-1)


def benchmark_tag(wd, tag, count, sudo):
    start = datetime.datetime.utcnow()
    print '-----------'
    print ' BENCHMARK '
    print '-----------'

    print 'Checking out tag "' + tag + '"'
    subprocess.check_call(['git', 'checkout', tag], **PIPEARGS)

    print 'Compiling using Makefile'
    subprocess.check_call(['make', 'clean', 'ep15'], **PIPEARGS)

    perfargs = ['make', 'perf']
    if sudo:
        perfargs = ['sudo'] + perfargs

    res = {}
    for i in range(count):

        print 'Run # ' + str(i) + ' ...'
        perfp = subprocess.Popen(perfargs, **PIPEARGS)
        (out, err) = perfp.communicate()

        outl = out.strip().split('\n')

        if len(outl) != 3 or outl[2] != EXPECTED:
            print 'Unexpected output, aborting.'
            print 'EXPECTED: ' + EXPECTED
            if len(outl) == 3:
                print 'ACTUAL: ' + outl[2]
            cleanup(wd)

        benchd = {'tag': tag}
        errl = err.strip().split('\n')
        for l in errl:
            m = re.match(r"^(\d+(,\d+)*){1}\s*([\w-]+).*?\(?(\d+\.\d+%)?\)?$",
                         l.strip())
            if m is not None:
                (count, name, percent) = m.group(1, 3, 4)
                benchd[name] = count.replace(',', '')
                if percent is None:
                    percent = ''
                benchd[name + '_percent'] = percent.strip('%')

            m = re.match(r"^(\d+(\.\d+))\s+seconds\s+time\s+elapsed$",
                         l.strip())
            if m is not None:
                benchd['seconds'] = m.group(1)
        res[i] = benchd

    end = datetime.datetime.utcnow()
    print ''
    print 'Total duration for this tag: ' + str(end - start)
    print ''
    return res

try:
    start = datetime.datetime.utcnow()
    curdir = os.getcwd()

    (wd, (resf, resfilename), tags) = setup()

    if len(sys.argv) > 2:
        count = int(sys.argv[2])
    else:
        count = ITERATIONS

    sudo = False
    if len(sys.argv) > 3:
        print 'Running benchmarks using sudo because argc > 3'
        sudo = True

    resf.write('time;i;' + ';'.join(EXPECTED_KEYS) + '\n')

    avgs = {}

    for t in tags:
            if t == 'HEAD':
                os.chdir(curdir)
            results = benchmark_tag(wd, t, count, sudo)
            sums = {}
            for k in EXPECTED_KEYS:
                if k != 'tag':
                    sums[k] = 0
            for i in results.keys():
                result = results[i]
                if set(result.keys()) == set(EXPECTED_KEYS):
                    output = str(start) + ';' + str(i) + ';'
                    for k in EXPECTED_KEYS:
                        if k != 'tag' and len(result[k]) > 0:
                            if isinstance(result[k], numbers.Integral):
                                sums[k] += long(result[k])
                            else:
                                sums[k] += float(result[k])
                        output += ';' + result[k]
                    resf.write(output + '\n')
                else:
                    print 'Discarding results from run #' + str(i) + ', wrong format'
                    print result
            for k in sums.keys():
                sums[k] = sums[k] / len(results.keys())
            avgs[t] = sums
            print 'Results saved'

    resf.close()

except:
    print ''
    print ''
    print '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
    print 'Exception encountered, cleaning up..'
    exctype, value = sys.exc_info()[:2]
    print exctype
    print value
    print '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
    print ''
    cleanup(wd)

cleanup(wd, False)

end = datetime.datetime.utcnow()

print '----------'
print '  RESULT  '
print '----------'
print 'Check ' + resfilename + ' for detailled results.'
print ''

last_tag = None
for t in avgs.keys():
    keys = avgs[t].keys()
    keys.sort()
    for k in keys:
        if k.endswith('percent'):
            del avgs[t][k]
            keys.remove(k)
    if last_tag is not None:
        print "Tag '" + t + "' (compared to '" + last_tag + "')"
        for k in keys:
            if abs(avgs[t][k]) < 5:
                valuestr = str(avgs[t][k])
            else:
                valuestr = str(round(avgs[t][k], 2))
            if avgs[last_tag][k] != 0:
                diff = round(avgs[t][k]*100/avgs[last_tag][k], 2)
                print '\t' + k + ': ' + valuestr + ' (' + str(diff) + '%)'
            elif avgs[t][k] != 0:
                print '\t' + k + ': ' + valuestr
    else:
        print "Tag '" + t + "'"
        for k in keys:
            if avgs[t][k] != 0:
                if abs(avgs[t][k]) < 5:
                    valuestr = str(avgs[t][k])
                else:
                    valuestr = str(round(avgs[t][k], 2))
                print '\t' + k + ': ' + valuestr
    last_tag = t

print ''
print 'Total duration for whole benchmark: ' + str(end - start)
