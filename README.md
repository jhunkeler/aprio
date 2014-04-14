# Automatic Priority Daemon

aprio was developed to enable systems administrators to automatically renice abusive, long running, CPU intensive
processes. In a shared high-computing environment, users may feel it is necessary to "compete" with each other's
programs, which often times leads to kernel load averages far exceeding an individual server's capabilities.

# Usage Output

usage: aprio.py [-h] [--daemon] [--logfile LOGFILE] [--user USER]
                [--cpu-threshold CPU_THRESHOLD]
                [--cputime-threshold CPUTIME_THRESHOLD]
                [--load-threshold LOAD_THRESHOLD] [--time-scale TIME_SCALE]
                [--poll POLL] [--test] [--verbose] [--quiet]

optional arguments:
  -h, --help            show this help message and exit
  --daemon, -d          Fork into background
  --logfile LOGFILE, -L LOGFILE
                        Log output to filename
  --user USER, -u USER  Limit to specific user
  --cpu-threshold CPU_THRESHOLD, -c CPU_THRESHOLD
                        Trigger after n%
  --cputime-threshold CPUTIME_THRESHOLD, -t CPUTIME_THRESHOLD
                        Trigger after {n}{smdwMy} Ex: 1d == 1 day
  --load-threshold LOAD_THRESHOLD, -l LOAD_THRESHOLD
                        Trigger after n load average
  --time-scale TIME_SCALE, -s TIME_SCALE
                        Time scale for nice value. Format: {n}{smdwMy} Ex: 1d
                        == 1 day
  --poll POLL, -p POLL  Wait n seconds between polling processes
  --test, -T            Do not modify processes; report only.
  --verbose, -v         Verbose output
  --quiet, -q           Suppress output


## Example

```bash
# aprio --daemon --cpu-theshold=85.0 --cputime-theshold=2h --load-threshold=10.0 --time-scale=2w
```

