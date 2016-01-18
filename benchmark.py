#!/usr/bin/python

import subprocess
import tempfile
import shutil
import os
import sys
import re
import datetime

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
    subprocess.check_call(['make', 'ep15'], **PIPEARGS)

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
                if percent == None:
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

start = datetime.datetime.utcnow()

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

for t in tags:
        results = benchmark_tag(wd, t, count, sudo)
        for i in results.keys():
            result = results[i]
            if set(result.keys()) == set(EXPECTED_KEYS):
                output = str(start) + ';' + str(i) + ';'
                for k in EXPECTED_KEYS:
                    output += ';' + result[k]
                resf.write(output + '\n')
            else:
                print 'Discarding results from run #' + str(i) + ', wrong format.'
                print result
        print 'Results saved'

resf.close()
cleanup(wd, False)

end = datetime.datetime.utcnow()

print '----------'
print '  RESULT  '
print '----------'
print 'Check ' + resfilename + ' for results.'
print 'Total duration for whole benchmark: ' + str(end - start)
