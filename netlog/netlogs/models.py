from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.contrib.postgres.fields import ArrayField

class User(AbstractUser):
	alphanumeric = RegexValidator(r'^[A-Za-z\-]*$', 'Only alphanumeric characters and dashes are allowed.')

	surname = models.CharField(max_length=100, validators=[alphanumeric])
	first_name = models.CharField(max_length=50, validators=[alphanumeric])
	last_name = models.CharField(max_length=100, validators=[alphanumeric])

	def get_user(self, user_id):
		return User.objects.get(id=user_id)

	def get_user_name(self, user_id):
		name =  User.objects.filter(id = user_id).values('first_name', 'last_name')
		fn = None
		ln = None
		if name:
			fn = name[0]['first_name']
			ln = name[0]['last_name']

		return fn, ln


class Hosts(models.Model):
	name = models.CharField(max_length=50)
	owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='host_monitoror', unique=False)
	is_ping = models.BooleanField(default=False)
	is_port = models.BooleanField(default=False)

	def __str__(self):
		return self.name

	def get_owner(self, host_id):
		hid = Hosts.objects.filter(id=host_id).values('owner_id')
		if hid:
			hid = hid[0]['owner_id']
		else:
			hid = None
		return hid

	def get_hosts_by_user_id(self, user_id):
		return Hosts.objects.filter(owner_id=user_id).order_by('-id').reverse()

	def get_hosts_by_id(self, id):
		return Hosts.objects.filter(id=id).order_by('-id').reverse()

	def update_is_ping(self, id, status):
		return Hosts.objects.filter(id=id).update(is_ping=status)

	def update_is_port(self, id, status):
		return Hosts.objects.filter(id=id).update(is_port=status)

	def get_host_name(self, owner_id, host_id):
		name =  Hosts.objects.filter(owner_id = owner_id, id = host_id).values('name')
		if name:
			name = name[0]['name']
		else:
			name = None
		return name

	def get_host_by_id(self, host_id):
		return Hosts.objects.filter(id=host_id)

	def delete_host(self, host_id):
		return Hosts.objects.get(id=host_id).delete()

	def is_monitoring(self, host_id):
		monitored =  Hosts.objects.filter(id = host_id).values('is_ping', 'is_port')
		ret = False
		if monitored:
			if monitored[0]['is_ping'] == True or monitored[0]['is_port'] == True:
				ret = True
		return ret

	def is_pinging(self, host_id):
		monitored =  Hosts.objects.filter(id = host_id).values('is_ping')
		ret = False
		if monitored:
			if monitored[0]['is_ping'] == True:
				ret = True
		return ret


class HostUsersMonitor(models.Model):
	host = models.ForeignKey(Hosts, on_delete=models.CASCADE, related_name='monitor_host', unique=False)
	start_time = models.DateTimeField(auto_now_add = True, unique=False) #when first created
	end_time = models.DateTimeField(auto_now=False, unique=False, blank=True)
	stopped_time = models.DateTimeField(auto_now=True, unique=False, blank=True)
	min_ms = models.FloatField(default=0)
	avg_ms = models.FloatField(default=0)
	max_ms = models.FloatField(default=0)
	transmited_pac = models.IntegerField(default=0)
	lost_pac = models.IntegerField(default=0)

	def create_monitor(self, host_id, end_time):
		return HostUsersMonitor.objects.create(host_id = host_id, end_time = end_time)


	def is_existing(self, user_id, host_id):
		exist = HostUsersMonitor.objects.filter(host_id = host_id)
		if exist:
			exist = True
		else:
			exist = False
		return exist

	def get_end_time(self, host_id):
		time = HostUsersMonitor.objects.filter(host = host_id).last()
		if time:
			time = time.end_time
		else:
			time = None
		return time


	def update_params(self, host_id, stopped_time, min_ms, avg_ms, max_ms, transmited_pac, lost_pac):
		hum_last = HostUsersMonitor.objects.filter(host_id=host_id).last()
		hum_last.stopped_time=stopped_time,
		hum_last.min_ms = min_ms
		hum_last.avg_ms = avg_ms
		hum_last.max_ms = max_ms
		hum_last.transmited_pac = transmited_pac
		hum_last.lost_pac = lost_pac
		hum_last.save()

	def get_info(self, host_id):
		monitored_before = HostUsersMonitor.objects.filter(host_id = host_id).select_related('host').last()
		if not monitored_before:
			monitored_before = PortMonitor.objects.filter(host_id = host_id).select_related('host').last()
			if not monitored_before:
				hm = Hosts()
				monitored_before = hm.get_hosts_by_id(id=host_id).values('name')
				if monitored_before:
					monitored_before = monitored_before[0]['name']
				else:
					monitored_before = "NONE"


		return monitored_before

	def get_stats(self, host_id, order):
		order = '-'+order
		monitored_before = HostUsersMonitor.objects.filter(host_id = host_id).order_by(order).values()
		if not monitored_before:
			return []
		return monitored_before

	def get_stats_date(self, host_id, order, date_start, date_end):
		order = '-'+order
		monitored_before = HostUsersMonitor.objects.filter(host_id = host_id, start_time__range=(date_start, date_end), stopped_time__range=(date_start, date_end)).order_by(order).values()
		if not monitored_before:
			return []
		return monitored_before



class PortMonitor(models.Model):
	host = models.ForeignKey(Hosts, on_delete=models.CASCADE, related_name='monitor_host_pm', unique=False)
	start_time = models.DateTimeField(auto_now_add = True, unique=False) #when first created
	end_time = models.DateTimeField(auto_now=False, unique=False, blank=True)
	stopped_time = models.DateTimeField(auto_now=True, unique=False, blank=True)
	ports = models.TextField(unique=False, blank=True)
	PROTOCOLS = [
		('tcp', 'TCP'),
		('udp', 'UDP'),
		('tcp/udp', 'TCP/UDP'),
	]

	protocol = models.CharField(max_length=9, choices=PROTOCOLS, default='tcp/udp',)
	results = models.TextField(unique=False, blank=True)

	def get_stats(self, host_id, order):
		order = '-'+order
		monitored_before = PortMonitor.objects.filter(host_id = host_id).order_by(order).values()
		if not monitored_before:
			return []
		return monitored_before

	def get_stats_date(self, host_id, order, date_start, date_end):
		order = '-'+order
		monitored_before = PortMonitor.objects.filter(host_id = host_id, start_time__range=(date_start, date_end), stopped_time__range=(date_start, date_end)).order_by(order).values()
		if not monitored_before:
			return []
		return monitored_before

	def create_port_monitor(self, host_id, end_time, ports, protocol):
		return PortMonitor.objects.create(host_id = host_id, end_time = end_time, ports=ports, protocol= protocol)

	def get_protocol_and_ports(self, host_id):
		info = PortMonitor.objects.filter(host = host_id).last()
		if info:
			ports = info.ports
			protocol = info.protocol
		else:
			ports = None
			protocol = None
		return protocol, ports

	def get_times(self, host_id):
		info = PortMonitor.objects.filter(host = host_id).values('start_time', 'end_time').last()
		if info:
			start_time = info['start_time']
			end_time = info['end_time']
		else:
			start_time = None
			end_time = None
		return start_time, end_time

	def get_info(self, host_id):
		return PortMonitor.objects.filter(host_id = host_id).last()


	def update_params(self, host_id, result):
		pm_last = PortMonitor.objects.filter(host_id=host_id).last()
		pm_last.results = result
		pm_last.save()

	def get_ports(self, host_id):
		pm_last = PortMonitor.objects.filter(host_id=host_id).values('ports').last()
		return pm_last