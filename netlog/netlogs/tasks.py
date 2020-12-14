from background_task import background
from background_task.models import Task
from time import sleep
import netlogs.ping.ping as ping
import os
from netlogs.models import HostUsersMonitor
from django.utils import timezone
from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session

import netlogs.port.portscan as portscan
import netlogs.helper as helper
import ast
	
@background()
def ping_every_2_sec(site, user_id, host_id):
	ms, timeout,msg = ping.ping(site, times = 1)

	for session in Session.objects.filter(expire_date__gt=timezone.now()):
		store = SessionStore(session_key=session.session_key)
		if store.get('_auth_user_id') in [user_id]:
			
			if host_id not in store:
				store[host_id] = {'num_of_seq': 0, 'max_ms': 0, 'min_ms': 9999, 'avg_ms': 0, 'num_timeout': 0, 'is_pinging': 1, 'down_seq': 0}
			else:
				store[host_id]['num_of_seq'] = int(store[host_id]['num_of_seq']) + 1
				if timeout != 0:
					store[host_id]['down_seq'] += 1
					store[host_id]['num_timeout'] = int(store[host_id]['num_timeout']) + 1
					store[host_id]['is_pinging'] = 0
					if store[host_id]['down_seq'] == 15:
						helper.send_email_ping(user_id, host_id)
				else:
					if (store[host_id]['is_pinging'] == 0):
						store[host_id]['is_pinging'] = 1
						store[host_id]['down_seq'] = 0

					if ms > store[host_id]['max_ms']:
						store[host_id]['max_ms'] = ms

					if ms < store[host_id]['min_ms']:
						store[host_id]['min_ms'] = ms

				store[host_id]['avg_ms'] = float(store[host_id]['avg_ms']) + ms
				print(store[host_id])
			store.save()

@background()
def check_port_3_sec(site, user_id, host_id, port_list, protocol):
	threads_count = helper.get_tread_counts(len(port_list))
	states = portscan.scan_ports_main(protocol, site, port_list, threads_count, 'all')
	for session in Session.objects.filter(expire_date__gt=timezone.now()):
		store = SessionStore(session_key=session.session_key)

		if int(store.get('_auth_user_id')) == user_id:
			key = "p_" + str(host_id)

			if key not in store:
				store[key] = "{}"
				temp = ast.literal_eval(store[key])
			else:
				temp = ast.literal_eval(store[key])
				
				send_to = {}
				email = False
				for port in states:
					if port[2] == "udp":
						key_local = "u_" + str(port[1])
					else:
						key_local = "t_" + str(port[1])

					if key_local not in temp:
						if port[3] == 'filtered' or port[3] == 'closed':
							temp[key_local] = {'state': 'down', 'seq': 1, 'down_seq': 1}
					else:
						if port[3] == 'filtered' or port[3] == 'closed':
							temp[key_local]['down_seq'] = int(temp[key_local]['down_seq']) + 1
							if temp[key_local]['state'] == 'down':
								temp[key_local]['seq'] = int(temp[key_local]['seq']) + 1
								if temp[key_local]['seq'] == 15:
									email = True
									send_to[key_local] = {'protocol': port[2], 'port': str(port[1]), 'state': temp[key_local]['state']}
							else:
								temp[key_local]['state'] = 'down'
								temp[key_local]['seq'] = 1
						else:

							if temp[key_local]['state'] == 'up':
								temp[key_local]['seq'] += 1
								
								'''
								if dic[key]['seq'] == 4:
									send email
								'''
							else:
								temp[key_local]['state'] = 'up'
								temp[key_local]['seq'] = 1

				if email:
					helper.send_email_ports(user_id, host_id, send_to)
				store[key] = str(temp)
				print(store[key])
			store.save()
	return

def stop_ping(host_name, user_id, host_id):
	
	search_param = '[["'+ host_name +'", "'+ user_id +'", "'+ host_id +'"], {}]'
	print(search_param)

	task_query = Task.objects.filter(task_params= search_param).values('task_hash')
	if task_query:
		hash_task = task_query[0]['task_hash']
		Task.objects.filter(task_hash = hash_task).delete()
		return True
	else:
		return False

def stop_port(host_name, user_id, host_id, port_list, protocol):

	search_param = '[["'+ host_name +'", '+ user_id +', '+ host_id +', '+ port_list +', '+ protocol+'], {}]'

	task_query = Task.objects.filter(task_params= search_param).values('task_hash')
	if task_query:
		hash_task = task_query[0]['task_hash']
		Task.objects.filter(task_hash = hash_task).delete()
		return True
	else:
		return False


def port_scan(protocol, port_list, host, threads_count, get_states):
	return portscan.scan_ports_main(protocol, host, port_list, threads_count, get_states)


