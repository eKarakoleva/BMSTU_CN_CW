from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
from django.utils import timezone
import netlogs.ping.ping as ping
import re
import ast
import netlogs.port.portscan as portscan
from django.core.mail import send_mail
from django.core.mail import EmailMultiAlternatives
import netlogs.models as models

def get_ping_params(host_id, user_id):
	
	for session in Session.objects.filter(expire_date__gt=timezone.now()):
		store = SessionStore(session_key=session.session_key)
		if store.get('_auth_user_id') in [user_id]:
			min_ms = store[host_id]['min_ms']
			avg_ms = store[host_id]['avg_ms']
			max_ms = store[host_id]['max_ms']
			transmited_pac = store[host_id]['num_of_seq']
			lost_pac = store[host_id]['num_timeout']
			if transmited_pac != 0:
				avg_ms = avg_ms / transmited_pac
			return min_ms, avg_ms, max_ms, transmited_pac, lost_pac 


def test_ping(host_name, times, msg_imp):
	return ping.ping(host_name, times, msg_imp)

def Sort(sub_li): 
    l = len(sub_li) 
    for i in range(0, l): 
        for j in range(0, l-i-1): 
            if (sub_li[j][1] > sub_li[j + 1][1]): 
                tempo = sub_li[j] 
                sub_li[j]= sub_li[j + 1] 
                sub_li[j + 1]= tempo 
    return sub_li 


def get_protocol(protocol):
	if protocol == "TCP" or protocol == 'tcp':
		return ['tcp']
	
	if protocol == "UDP" or protocol == 'udp':
		return ['udp']

	if protocol == "TCP/UDP" or protocol == 'tcp/udp':
		return ['tcp', 'udp']

	#return ['tcp', 'udp']

def prepare_port_list(port_list):
	port_list = port_list.replace('"','')
	port_list = re.sub(' +', ' ', port_list)

	if port_list == "all":
		return portscan.SERVICE_PORTS_TCP

	if port_list != "":
		port_list = [int(n) for n in port_list.split(' ')]
	else:
		port_list = 0

	
	if port_list != 0:
		port_list = [number for number in port_list if number < 65535]

	return port_list

def round(num):
	if num % 10 >= 0.5:
		return int(num + 1)
	else:
		return int(num)

def get_tread_counts(list_len):
	temp = list_len / 3
	threads = round(temp + temp /2)
	return threads


def format_protocols_to_array(protocol):
	if protocol == "tcp/udp":
		protocol = '["tcp", "udp"]'
	else:
		if protocol == "udp":
			protocol = '["udp"]'
		else:
			protocol = '["tcp"]'
	return protocol


def get_port_monitor_results(host_id, user_id):
	for session in Session.objects.filter(expire_date__gt=timezone.now()):
		store = SessionStore(session_key=session.session_key)
		if int(store.get('_auth_user_id')) == user_id:
			key = "p_" + str(host_id)
			temp = ast.literal_eval(store[key])
			results = {}
			for lp in temp:
				results[lp] = temp[lp]['down_seq']
	return results


def get_port_monitor_downs(host_id, user_id):
	for session in Session.objects.filter(expire_date__gt=timezone.now()):
		store = SessionStore(session_key=session.session_key)
		if int(store.get('_auth_user_id')) == user_id:
			key = "p_" + str(host_id)
			temp = ast.literal_eval(store[key])
			results = []
			for lp in temp:
				if temp[lp]['state'] == 'down':
					results.append(lp)
	return results


def get_criteria(cr):

	d = {
		'Start': 'start_time',
		'End': 'end_time',
		'Avg ms': 'avg_ms',
		'Min ms': 'min_ms',
		'Max ms': 'max_ms',
		'Total packets': 'transmited_pac',
		'Lost packets': 'lost_pac'
	}

	return d.get(cr, cr)

def format_port_monitor_results(stats):
	results = {'tcp': {}, 'udp': {}}
	new_stats = {}
	for stat in stats:
		if stat['results'] != "":
			temp = ast.literal_eval(stat['results'])
			results = {'tcp': {}, 'udp': {}}
			for t in temp:
				new_stats = {}
				tsplit = t.split("_")
				new_stats[tsplit[1]] = temp[t] 
				if tsplit[0] == "t":
					results['tcp'].update(new_stats)
				else:
					results['udp'].update(new_stats)
			stat['results'] = results
		else:
			stat['results'] = {'tcp': {}, 'udp': {}}
	return stats


def send_email_ports(user_id, host_id, ports):
	h = models.Hosts()
	host_name = h.get_host_name(user_id, host_id)
	us = models.User()
	fn, ln = us.get_user_name(user_id)

	subject, from_email, to = 'Some port(s) are down!', 'karakolevaed@student.bmstu.ru', 'elenakarakoleva@gmail.com'
	html_content = '<p>Hello <b>'+ fn + ' '+ ln + ' </b>! <br> I want to notify you that port number(s) '
	text_content = 'This is an important message.'
	ports_str = ''
	for port in ports:
		ports_str += '<b>' + ports[port]['port'] + '('+ports[port]['protocol']+')' + '</b>, '
	html_content += ports_str +' on your host <b>'+host_name+'</b> is (are) <b> DOWN </b>!</p>'
	msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
	msg.attach_alternative(html_content, "text/html")
	msg.send()

def send_email_ping(user_id, host_id):
	h = models.Hosts()
	host_name = h.get_host_name(user_id, host_id)
	us = models.User()
	fn, ln = us.get_user_name(user_id)

	subject, from_email, to = 'Your host is down!', 'karakolevaed@student.bmstu.ru', 'elenakarakoleva@gmail.com'
	html_content = '<p>Hello <b>'+ fn + ' '+ ln + ' </b>! <br> I want to notify you that your host <b>' + host_name + '</b> is <b>DOWN</b>'
	text_content = 'This is an important message.'
	msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
	msg.attach_alternative(html_content, "text/html")
	msg.send()

