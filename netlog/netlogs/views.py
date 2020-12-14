from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import render, redirect
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,UpdateView)
import netlogs.models as models
from netlogs.forms import UserSignUpForm, HostsForm, HostUsersMonitorForm, PortMonitorForm, UserForm
from django.urls import reverse_lazy, reverse
from django.http import HttpResponse, JsonResponse, Http404
import netlogs.tasks as task
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta, datetime
from background_task.models import Task
from django.contrib.auth.decorators import login_required

import netlogs.ping.ping as ping
import netlogs.helper as helper
import json
import ast
from django.core.mail import send_mail
import requests



class UserSignUpView(CreateView):
	model = models.User
	form_class = UserSignUpForm
	template_name = 'registration/signup_form.html'
	success_url = reverse_lazy('login')

	def get_context_data(self, **kwargs):
		return super().get_context_data(**kwargs)

	def form_valid(self, form):
		user = form.save()
		return redirect('index')

@login_required
def view_hosts(request, pk):
	modelHosts = models.Hosts();
	user_hosts = modelHosts.get_hosts_by_user_id(user_id = request.user.id)
	return render(request, 'hosts_list.html', {'id': pk, 'hosts': user_hosts})

@login_required
def get_monitored_ports(request):
	ids = json.loads(request.GET.get('ids'))
	pm = models.PortMonitor()
	monitored = {}
	for idd in ids:
		temp = {}
		ports = pm.get_ports(idd)
		temp['ports'] = ports
		temp['count'] = len(list(ports['ports'].split(" ")))
		monitored[str(idd)] = temp
			
	data = {
		'status': monitored
	}
	return JsonResponse(data)

@login_required
def get_down_ports(request):
	ids = json.loads(request.GET.get('ids'))
	downs = {}
	for idd in ids:
		temp = {}
		ports = helper.get_port_monitor_downs(idd, request.user.id)
		temp['ports'] = ports
		temp['count'] = len(ports)

		downs[str(idd)] = temp
			
	data = {
		'status': downs
	}
	return JsonResponse(data)


class HostCreateView(CreateView):
	model = models.Hosts
	form_class = HostsForm
	template_name = 'add/add_host.html'
	
	def form_valid(self, form):
		course = form.save(commit=False)
		course.owner = self.request.user
		course.save()
		#messages.success(self.request, 'The course was created with success! Go ahead and add some quizzes now.')
		return redirect('index')


@login_required
def start_ping(request, pk, template_name='modals/start_ping.html'):
	model_hum = models.HostUsersMonitor()
	host_m = models.Hosts()
	owner_id = host_m.get_owner(pk)

	if owner_id == request.user.id:
		form = HostUsersMonitorForm(request.POST or None)	
		if form.is_valid():
			date = form.cleaned_data['end_time']
			if date == None:
				date = timezone.now() + timedelta(1)
			model_hum.create_monitor(pk, date)
			model_host = models.Hosts()
			model_host.update_is_ping(pk, True)
			host_name = model_host.get_host_name(request.user.id, pk)

			session_exist = request.session.get(str(pk))
			if not session_exist:
				request.session[str(pk)] = {'num_of_seq': 0, 'max_ms': 0, 'min_ms': 9999, 'avg_ms': 0, 'num_timeout': 0, 'is_pinging': 1, 'down_seq': 0}

			task.ping_every_2_sec(host_name, str(request.user.id), str(pk), repeat=2, repeat_until = date)

			return HttpResponse(render_to_string('modals/item_edit_form_success.html'))
		return render(request, template_name, {'form':form, 'id': pk})
	raise Http404


class stopPing(UpdateView):
	def  get(self, request):
		host_id = request.GET.get('id', None)
		model_host = models.Hosts()
		host_name = model_host.get_host_name(request.user.id, host_id)
		success = task.stop_ping(host_name, str(request.user.id), str(host_id))
		if success:
			session_exist = request.session.get(str(host_id))
			if session_exist:
				del request.session[str(host_id)]
				hum = models.HostUsersMonitor()
				min_ms, avg_ms, max_ms, transmited_pac, lost_pac = helper.get_ping_params(str(host_id), str(request.user.id))
				hum.update_params(host_id, timezone.now(), min_ms, avg_ms, max_ms, transmited_pac, lost_pac)

				model_host.update_is_ping(host_id, False)
				messages.success(request, 'You are not pinging now!')
			else:
				messages.error(request, 'Something went wrong!')
		data = {
			'stopped': success
		}
		return JsonResponse(data)

@login_required
def view_host_settings(request, pk):
	host_m = models.Hosts()
	owner_id = host_m.get_owner(pk)

	if owner_id == request.user.id:
		hum = models.HostUsersMonitor()
		user_hosts = hum.get_info(pk)
		pm = models.PortMonitor()
		port_m_info = pm.get_info(pk)
	else:
		raise Http404

	return render(request, 'settings_list.html', {'id': int(pk), 'host': user_hosts, 'user_id': request.user.id, 'p_times': port_m_info})

@login_required
def status_update(request):		
	ids = json.loads(request.GET.get('ids'))

	active_pings = {}
	for idd in ids:
		session_exist = request.session.get(str(idd))
		#host_m = models.Hosts()
		if session_exist:
			#is_pinging = host_m.is_pinging(idd)
			#if not is_pinging:
				#del request.session[str(idd)]
			active_pings[str(idd)] = session_exist['is_pinging']

	data = {
		'status': active_pings
	}
	return JsonResponse(data)

@login_required
def check_if_expired(request):

	ids = json.loads(request.GET.get('ids'))
	hum = models.HostUsersMonitor()
	pm = models.PortMonitor()
	success = True
	for idm in ids:
		end_time = hum.get_end_time(idm)
		st, end_time_port = pm.get_times(idm)

		model_host = models.Hosts()
		host_name = model_host.get_host_name(request.user.id, idm)
		
		if end_time:
			if end_time < timezone.now():
				success = task.stop_ping(host_name, str(request.user.id), str(idm))
				if success:
					min_ms, avg_ms, max_ms, transmited_pac, lost_pac = helper.get_ping_params(str(idm), str(request.user.id))
					hum.update_params(idm, timezone.now(), min_ms, avg_ms, max_ms, transmited_pac, lost_pac)

					session_exist = request.session.get(str(idm))
					if session_exist:
						del request.session[str(idm)]
					model_host.update_is_ping(idm, False)

		if end_time_port:
			if end_time_port < timezone.now():
				protocol, ports = pm.get_protocol_and_ports(idm)
				protocol = helper.format_protocols_to_array(protocol)

				success = task.stop_port(host_name, str(request.user.id), str(idm), str(ports), protocol)
				if success:
					key = "p_" + str(idm)
					session_exist = request.session.get(key)
					if session_exist:
						result = helper.get_port_monitor_results(idm, request.user.id)
						del request.session[key]

						pm.update_params(idm, str(result))
						model_host.update_is_port(idm, False)

	data = {
		'status': success
	}    
	return JsonResponse(data)

@login_required
def test_ping(request):
	
	h_id = request.GET.get('id', None)
	model_host = models.Hosts()
	data = {
		'response': "Not your host"
	}
	owner_id = model_host.get_owner(h_id)
	if owner_id == request.user.id:
		host_name = model_host.get_host_name(request.user.id, h_id)
		ms, timeout, msg = helper.test_ping(host_name, 4, 1)
		data = {
			'response': msg
		}

	return JsonResponse(data)

@login_required
def get_host_geoinfo(request):
	h_id = request.GET.get('id', None)
	model_host = models.Hosts()

	owner_id = model_host.get_owner(h_id)

	if owner_id == request.user.id:
		host_name = model_host.get_host_name(request.user.id, h_id)
		ip_addr = ping._to_ip(host_name, False)
		url = 'https://extreme-ip-lookup.com/json/'+ str(ip_addr)
		r = requests.get(url)
		data = json.loads(r.content.decode())

		data = {
			'response': data
		}
	else:
		data = {
			'response': None
		}

	return JsonResponse(data)

@login_required
def scan_given_ports(request):
	port_list = request.GET.get('ports', None)
	h_id = request.GET.get('id', None)
	model_host = models.Hosts()
	owner_id = model_host.get_owner(h_id)

	data = {
		'response': [' none']
	}

	if owner_id == request.user.id:
		host_name = model_host.get_host_name(request.user.id, h_id)
		prot = request.GET.get('protocol', None)
		get_states = request.GET.get('state', None)
		protocol = helper.get_protocol(prot)

		port_list = helper.prepare_port_list(port_list)

		if port_list != 0:
			threads = helper.get_tread_counts(len(port_list))
			states = task.port_scan(protocol, port_list, host_name, threads, get_states)

			data = {
				'response': helper.Sort(states)
			}

	return JsonResponse(data)

@login_required
def start_port(request, pk, template_name='modals/start_port.html'):
	model_pm = models.PortMonitor()
	model_host = models.Hosts()
	owner_id = model_host.get_owner(pk)

	if owner_id == request.user.id:	
		form = PortMonitorForm(request.POST or None)	
		if form.is_valid():
			model_host = models.Hosts()
			host_name = model_host.get_host_name(request.user.id, pk)


			date = form.cleaned_data['end_time']
			ports = form.cleaned_data['ports']
			prot = form.cleaned_data['protocol']
			protocol = helper.get_protocol(prot)

			port_list = helper.prepare_port_list(ports)


			key = "p_" + str(pk)
			session_exist = request.session.get(key)
			if not session_exist:
				request.session[key] = "{}"

			task.check_port_3_sec(host_name, request.user.id, pk, port_list, protocol, repeat=1, repeat_until = date)
			if len(protocol) == 2:
				protocol = "tcp/udp"
			else:
				protocol = protocol[0]

			model_pm.create_port_monitor(pk, date, str(port_list), protocol)
			

			model_host.update_is_port(pk, True)

			return HttpResponse(render_to_string('modals/item_edit_form_success.html'))
		return render(request, template_name, {'form':form, 'id': pk})
	raise Http404


class stopPort(UpdateView):
	def  get(self, request):
		host_id = request.GET.get('id', None)
		model_host = models.Hosts()
		status = False

		owner_id = model_host.get_owner(host_id)
		if owner_id == request.user.id:
			host_name = model_host.get_host_name(request.user.id, host_id)
			models_pm = models.PortMonitor()
			protocol, ports = models_pm.get_protocol_and_ports(host_id)
			protocol = helper.format_protocols_to_array(protocol)

			task.stop_port(host_name, str(request.user.id), str(host_id), str(ports), protocol)

			key = "p_" + str(host_id)
			session_exist = request.session.get(key)


			if session_exist:
				result = helper.get_port_monitor_results(host_id, request.user.id)
				del request.session[key]

				pm = models.PortMonitor()
				pm.update_params(host_id, str(result))
				model_host.update_is_port(host_id, False)

				messages.success(request, 'You are not port monitoring now!')
				status = False
			else:
				messages.error(request, 'Something went wrong!')
		data = {
			'stopped': status
		}

		return JsonResponse(data)

@login_required
def status_update_port(request):		
	ids = json.loads(request.GET.get('ids'))

	active_ports = {}
	for idd in ids:
		key = "p_" + str(idd)
		session_exist = request.session.get(key)
		if session_exist:
			downs= helper.get_port_monitor_downs(idd, request.user.id)
			
	data = {
		'status': str(downs)
	}
	return JsonResponse(data)

@login_required
def stat_list_ping(request, pk):
	hum = models.HostUsersMonitor()
	stats = hum.get_stats(pk, 'id')
	hm = models.Hosts()
	owner_id = hm.get_owner(pk)

	if owner_id == request.user.id:	
		name = hm.get_host_name(request.user.id, pk)
		return render(request, 'stat_list_ping.html', {'id': int(pk), 'stats': stats, 'name':name})
	raise Http404

@login_required
def sort_ping_stats(request):		

	id_p = request.GET.get('id_p')
	criretia = request.GET.get('criretia')
	date_start = request.GET.get('tstart')
	date_end = request.GET.get('tend')

	hum = models.HostUsersMonitor()
	criretia = helper.get_criteria(criretia)
	
	if date_start == "" or date_end == "":
		stats = hum.get_stats(id_p, criretia)
	else:
		stats = hum.get_stats_date(id_p, criretia, date_start, date_end)

	data = {
		'stats': list(stats)
	}

	return JsonResponse(data,  safe=True)

@login_required
def stat_list_port(request, pk):
	pm = models.PortMonitor()
	stats = pm.get_stats(pk, 'id')
	hm = models.Hosts()
	owner_id = hm.get_owner(pk)

	if owner_id == request.user.id:	
		name = hm.get_host_name(request.user.id, pk)
		stats = helper.format_port_monitor_results(stats)
		return render(request, 'stat_list_port.html', {'id': int(pk), 'stats': stats, 'name':name})
	raise Http404

@login_required
def sort_port_stats(request):		

	id_p = request.GET.get('id_p')
	criretia = request.GET.get('criretia')
	date_start = request.GET.get('tstart')
	date_end = request.GET.get('tend')

	pm = models.PortMonitor()
	criretia = helper.get_criteria(criretia)
	if date_start == "" or date_end == "":
		stats = pm.get_stats(id_p, criretia)
	else:
		stats = pm.get_stats_date(id_p, criretia, date_start, date_end)
	stats = helper.format_port_monitor_results(stats)
	data = {
		'stats': list(stats)
	}

	return JsonResponse(data,  safe=True)

@login_required
def delete_host(request):		

	id_h = request.GET.get('id')

	hm = models.Hosts()

	owner_id = hm.get_owner(id_h)
	stat = False
	if owner_id == request.user.id:
		is_mon = hm.is_monitoring(id_h)
		
		if is_mon:
			messages.error(request, 'Please stop all monitoring activities before delete')
			stat = True

		else:
			hm.delete_host(id_h)
			messages.success(request, 'Success!')

	data = {
		'stats': stat
	}
	return JsonResponse(data,  safe=True)

@login_required
def edit_profile(request):
	user_inst = get_object_or_404(models.User, id=request.user.id)
	my_form = UserForm(request.POST or None, instance=user_inst)

	if my_form.is_valid():
		my_form.save()
		messages.success(request, 'Data is updated successfuly!')

	return render(request, 'update_user.html', {'form': my_form})