#!/usr/bin/env python
import os
import time
try:
	import psutil
except ImportError:
	print("psutil module not found!")
	exit(1)

try:
	import argparse
except ImportError:
	print("argparse module not found!")
	exit(1)


class Elapsed(object):
	SECOND = 1
	MINUTE = SECOND * 60
	HOUR = MINUTE * 24
	DAY = HOUR * 24
	WEEK = DAY * 7

LOAD_THRESHOLD=1
try:
	LOAD_THRESHOLD=psutil.cpu_count() / 2
except:
	LOAD_THRESHOLD=psutil.cpu_count()
CPU_THRESHOLD=50.0
CPUTIME_THRESHOLD=Elapsed.SECOND * 1
POLL=3
TEST_MODE=False
VERBOSE=False
QUITE=False

def renice(proc, nice_value=0):
	nice_current = 255
	try:
		pid = proc.pid
		nice_previous = proc.get_nice()
		
		if nice_previous < 0:
			return

		if nice_value <= nice_previous:
			return

		if not TEST_MODE:
			proc.set_nice(nice_value)

		if not TEST_MODE:
			nice_current = proc.get_nice()
		else:
			nice_current = nice_value

		print("PID: {0}: nice({1}) -> nice({2})".format(pid, nice_previous, nice_current))
	except psutil.AccessDenied as e:
		print("PID: {0}: {1}: Permission denied setting nice to {2}".format(pid, proc.username(), nice_value))
	except psutil.NoSuchProcess as e:
		return
	return nice_current

def time_to_nice(start_time):
	nice = 0
	diff = time.time() - start_time
	if diff >= Elapsed.WEEK:
		nice = 19
	elif diff >= Elapsed.DAY:
		nice = 15
	elif diff >= Elapsed.DAY / 2:
		nice = 11
	elif diff >= Elapsed.HOUR:
		nice = 9
	elif diff >= Elapsed.HOUR / 2:
		nice = 4
	elif diff >= Elapsed.MINUTE:
		nice = 2
	elif diff >= Elapsed.MINUTE / 2:
		nice = 1
	
	return nice	

def cputime_to_nice(cpu_time):
	nice = 0
	time_user, time_system = cpu_time
	diff = time_user + time_system
	if diff >= Elapsed.WEEK:
		nice = 19
	elif diff >= Elapsed.DAY:
		nice = 15
	elif diff >= Elapsed.DAY / 2:
		nice = 11
	elif diff >= Elapsed.HOUR:
		nice = 9
	elif diff >= Elapsed.HOUR / 2:
		nice = 4
	elif diff >= Elapsed.MINUTE:
		nice = 2
	elif diff >= Elapsed.MINUTE / 2:
		nice = 1
		
	return nice	

def get_bad_processes(cpu_threshold=CPU_THRESHOLD, cputime_threshold=CPUTIME_THRESHOLD, *args, **kwargs):
	user = ""
	if kwargs.has_key('user'):
		user = kwargs['user']

	for proc in psutil.process_iter():
		try:
			pid = proc.pid
			username = proc.username()
			status = proc.status()
			started = proc.create_time()
			user_time, system_time = proc.cpu_times()
			cputime_total = user_time + system_time
			uid, euid, _ = proc.uids()

			if uid == 0 or euid == 0:
				continue


			cpu = proc.get_cpu_percent(interval=0.05)
			if cpu > cpu_threshold:
				if VERBOSE:
					print("PID: {0}: cpu_threshold exeeded ({1}% > {2}%)".format(pid, cpu, cpu_threshold))
				if cputime_total > cputime_threshold:
					if VERBOSE:
						print("PID: {0}: cputime_threshold exceeded ({1} > {2})".format(pid, cputime_total, cputime_threshold))
					if user:
						if user != username:
							continue
					yield proc

		except psutil.NoSuchProcess as e:
			if VERBOSE:
				print("PID: {0}: disappeared".format(e.pid))

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument('--user', '-u', default="", type=str, help='Limit to specific user')	
	parser.add_argument('--cpu-threshold', '-c', default=CPU_THRESHOLD, type=float, help='Trigger after n%%')
	parser.add_argument('--cputime-threshold', '-t', default=CPUTIME_THRESHOLD, type=float, help='Trigger after n%%')
	parser.add_argument('--load-threshold', '-l', default=LOAD_THRESHOLD, type=float, help='Trigger after n load average')
	parser.add_argument('--poll', '-p', default=POLL, type=float, help='Wait n seconds between polling processes')
	parser.add_argument('--test', '-T', action='store_true', default=False, help='Do not modify processes; report only.')
	parser.add_argument('--verbose', '-v', action='store_true', default=False, help='Verbose output')
	parser.add_argument('--quiet', '-q', action='store_true', default=False, help='Suppress output')
	
	args = parser.parse_args()

	POLL = args.poll
	VERBOSE = args.verbose
	QUIET = args.quiet
	TEST_MODE = args.test
	CPU_THRESHOLD = args.cpu_threshold
	CPUTIME_THRESHOLD = args.cputime_threshold
	LOAD_THRESHOLD = args.load_threshold
	user = args.user
	
	
	load_sleep = False
	load_warn = False

	while(True):
		load = os.getloadavg()
		load = sum(load) / len(load)
		if load < LOAD_THRESHOLD:
			load_sleep = True
			load_warn = False
			if load_sleep:
				if VERBOSE:
					print("SYS: load_threshold nominal, sleeping ({0} < {1})".format(load, LOAD_THRESHOLD))
			load_sleep = False
			time.sleep(POLL)
			continue
		else:
			load_warn = True

		if load_warn:
			if VERBOSE:
				print("SYS: load_threshold exceeded ({0} > {1})".format(load, LOAD_THRESHOLD))

		for bad in get_bad_processes(CPU_THRESHOLD, CPUTIME_THRESHOLD, user=user):
			try:
				nice = cputime_to_nice(bad.cpu_times())

				if not nice:
					nice = time_to_nice(bad.create_time())

				if nice != 0:
		  			renice(bad, nice)

			except psutil.NoSuchProcess:
				continue
		time.sleep(POLL)
