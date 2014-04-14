# Automatic Priority Daemon

Aprio was developed to enable systems administrators to automatically renice abusive, long running, CPU intensive
processes. In a shared high-computing environment, users may feel it is necessary to "compete" with each other's
programs, which often times leads to kernel load averages far exceeding an individual server's capabilities.

# Usage Output
```
usage: aprio.py [-h] [--daemon] [--logfile LOGFILE] [--user USER]
                [--cpu-threshold CPU_THRESHOLD]
                [--cputime-threshold CPUTIME_THRESHOLD]
                [--load-threshold LOAD_THRESHOLD] [--time-scale TIME_SCALE]
                [--poll POLL] [--test] [--verbose] [--quiet]

optional arguments:
  -h, --help            show this help message and exit
  --daemon, -d          Fork into background (default: False)
  --logfile LOGFILE, -L LOGFILE
                        Log output to filename (default: None)
  --user USER, -u USER  Limit to specific user (default: None)
  --cpu-threshold CPU_THRESHOLD, -c CPU_THRESHOLD
                        Trigger after n% (default: 50.0)
  --cputime-threshold CPUTIME_THRESHOLD, -t CPUTIME_THRESHOLD
                        Trigger after {n}{smdwMy} (default: 30m)
  --load-threshold LOAD_THRESHOLD, -l LOAD_THRESHOLD
                        Trigger after n load average (default: 4)
  --time-scale TIME_SCALE, -s TIME_SCALE
                        Scale by which nice values are calculated {n}{smdwMy}
                        (default: 1w)
  --poll POLL, -p POLL  Wait n seconds between polling processes (default: 3)
  --test, -T            Do not modify processes; report only. (default: False)
  --verbose, -v         Verbose output (default: False)
  --quiet, -q           Suppress output (default: False)

```

## Examples

### As a daemon process

```bash
aprio --daemon --cpu-threshold=85.0 --cputime-threshold=2h --load-threshold=10.0 --time-scale=2w
```

### As a foreground process

The default loglevel is INFO. Aprio will only report changes to process priority.

```bash
aprio --cpu-threshold=85.0 --cputime-threshold=2h --load-threshold=10.0 --time-scale=2w
INFO:2014-04-14 09:31:18,872:renice:13481:Priority modified (0 -> 20)
```

### Controlling a single user

The `--user` or `-u` argument allows you to target a user's processes.

```bash
aprio --user=foo --cpu-threshold=85.0 --cputime-threshold=2h --load-threshold=10.0 --time-scale=2w
```

