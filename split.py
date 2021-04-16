#!/usr/bin/env python

import json
import logging
import os
import subprocess
import sys
import time
import argparse
import re

from os import listdir
from os.path import isfile, isdir, join




parser = argparse.ArgumentParser(description='split logs for each test case.')
parser.add_argument('log_dir', metavar='log_dir', type=str, 
                    help='build log dir')

args = parser.parse_args()

log_dir = args.log_dir

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')

build_log = args.log_dir + "/build-log.txt"
build_log_out_dir = build_log + ".sp"
build_log_out_dir_err = build_log_out_dir + ".err"
if not isdir(build_log_out_dir):
    os.mkdir(build_log_out_dir)
if not isdir(build_log_out_dir_err):
    os.mkdir(build_log_out_dir_err)

if not os.path.isfile(build_log):
    logger.info(f"build log file not exist {build_log}")
    quit()

start = re.compile("^(.\d{4} \d{2}:\d{2}:\d{2}\.\d{3}\] )?\[BeforeEach\].*")
end = re.compile(".* Destroying namespace \"(.*)\" for this suite.*")
endNamespace = re.compile(".*Waiting for namespaces \[(.*)\] to vanish.*")
skip = re.compile(".*\[SKIPPING\].*")
summary = re.compile(".*m(\d+) Passed.* \| .*m(\d+) Failed.* \| .*m(\d+) Pending.* \| .*m(\d+) Skipped.*")
failure = re.compile(".*Failure \[\d+\.\d+ .*\].*")
namespaces = []
results = {}
#summary = re.compile(".*Passed.*Failed.*Pending.*Skipped.*")
# start 
#       [BeforeEach]
# end:  
#       STEP: Destroying namespace "container-runtime-7928" for this suite.
#           continue to next [BeforeEach], set as end
#           extract namespace
#           write start/end to separte file
#           continue
#   OR
#       [SKIPPING]  
#           discard tmp data
#           continue  
with open(build_log) as bf:
    store = ""
    namespace = ""
    matching = False
    matchingEnd = False
    failed = False

    for line in bf:
        #print(line)
        if start.match(line):
            if matchingEnd:
                outdir = build_log_out_dir
                if failed:
                    outdir = build_log_out_dir_err
                with open(join(outdir, namespace), 'w') as pf:
                    pf.write(store)
                print("found match for namespace", namespace, "failed: ", failed)
                store = ""
                namespace = ""
                matching = False
                matchingEnd = False
                failed = False

            matching = True
            store = store + line
        elif summary.match(line):
            outdir = build_log_out_dir
            if failed:
                outdir = build_log_out_dir_err
            with open(join(outdir, namespace), 'w') as pf:
                pf.write(store)
            print("found match for namespace at the end", namespace, "failed: ", failed)
            break
            store = ""
            namespace = ""
            matching = False
            failed = False
        elif skip.match(line):
            matching = False
            store = ""
            continue
        elif end.match(line) or endNamespace.match(line):
            store += line
            # if already found end, and another end coming, means there are multiple ns to be destroyed, we just pick the first one which should have the common prefix
            if matchingEnd:    
                continue

            m = end.match(line)
            if not m:
                m = endNamespace.match(line)
            namespace = m.group(1)
            namespaces.append(namespace)

            # now we found the destroying line, continue to the next BeforeEach, then write the data
            matchingEnd = True
            continue 
        else:
            if matching:
                store += line
            if matchingEnd:
                if failure.match(line):
                    failed = True


art_dir = join(log_dir,"artifacts")
dirs = [f for f in listdir(art_dir) if isdir(join(art_dir, f))]
#rep = re.compile(".*(" + "|".join(namespaces) + ").*")

nsprefix={}
for n in namespaces:
    sp = n.split("-")
    newarr = [st for st in sp if not st.isdecimal()]
    nsprefix["-".join(newarr)]=""

prefix = "(" + "|".join(nsprefix) + ")"
sufix = "((-\d{1,4}))"
rep = re.compile(".*(" + prefix + sufix + ").*")

teststr = "I0331 18:34:44.120761      10 eventhandlers.go:279] \"Delete event for scheduled pod\" pod=\"csi-mock-volumes-1570-6273/csi-mockplugin-0\""
m = rep.match(teststr)
if m:
    print(m.group(1))


for d in dirs:
    dir=join(art_dir, d)
    files = [f for f in listdir(dir) if isfile(join(dir, f))]
    for file in files:
        if not file.endswith(".log"):
            continue
        for n in namespaces:
            results[n] = []

        with open(join(dir,file)) as bf:
            for line in bf:
                m = rep.match(line)
                if m:
                    ns = m.group(1)

                    # this ns may not be the exact one
                    if ns in results:
                        results[ns].append(line)
        # write file
        
        outdir = join(dir, file+".sp")
        
        print(outdir)

        for n in namespaces:
            if results[n]:
                if not os.path.isdir(outdir):
                    os.mkdir(outdir)
                with open(join(outdir, n), "w") as f:
                    f.writelines(results[n])


