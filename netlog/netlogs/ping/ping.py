import select
import socket
import struct
import sys
import os
import time

PACKET_SIZE_CONST = 55
TIMEOUT_CONST = 1000
ICMP_ECHO_CONST = 8
ICMP_MAX_RECV_CONST = 2048
MAX_WAIT = 1000


ICMP_ECHOREPLY = 0          # Echo reply (per RFC792)
ICMP_ECHO_IPV6 = 128        # Echo request (per RFC4443)
ICMP_ECHO_IPV6_REPLY = 129  # Echo request (per RFC4443)


ICMP_ECHO = 8               # Echo request (per RFC792)
ICMP_PORT = 1
ICMP_PORT_IPV6 = 58
ICMP_MAX_RECV = 2048 

if sys.platform.startswith("win32"):
	timer = time.perf_counter
else:
	timer = time.time


def _is_valid_ip(addr, version):
	try:
		socket.inet_aton(addr)
	except socket.error:
		return False
	return True


def _to_ip(addr, is_ipv6):
	"""
	If destination is not ip address, resolve it by using hostname
	"""

	try:
		if is_ipv6:
			info = socket.getaddrinfo(addr, None)[0]
			destination_ip = info[4][0]
			return destination_ip
		else:
			return socket.gethostbyname(addr)
	except socket.error:
		return -1


def _checksum(source_string):

	count_to = (int(len(source_string)/2))*2
	sum = 0
	count = 0

	# Handle bytes in pairs (decoding as short ints)
	lo_byte = 0
	hi_byte = 0
	while count < count_to:
		if (sys.byteorder == "little"):
			lo_byte = source_string[count]
			hi_byte = source_string[count + 1]
		else:
			lo_byte = source_string[count + 1]
			hi_byte = source_string[count]
		try:     # For Python3
			sum = sum + (hi_byte * 256 + lo_byte)
		except:  # For Python2
			sum = sum + (ord(hi_byte) * 256 + ord(lo_byte))
		count += 2

	# Handle last byte if applicable (odd-number of bytes)
	# Endianness should be irrelevant in this case
	if count_to < len(source_string): # Check for odd length
		lo_byte = source_string[len(source_string)-1]
		try:      # For Python3
			sum += lo_byte
		except:   # For Python2
			sum += ord(lo_byte)

	sum &= 0xffffffff # Truncate sum to 32 bits (a variance from ping.c, which
						  # uses signed ints, but overflow is unlikely in ping)

	sum = (sum >> 16) + (sum & 0xffff)    # Add high 16 bits to low 16 bits
	sum += (sum >> 16)                    # Add carry from above (if any)
	answer = ~sum & 0xffff                # Invert and truncate to 16 bits
	answer = socket.htons(answer)
	return answer


def _parse_icmp_header(packet):
	icmp_header_keys = ('type', 'code', 'checksum', 'packet_id', 'sequence')
	return dict(zip(icmp_header_keys, struct.unpack("!BBHHH", packet[20:28])))

def _parse_ip_header(packet):
	ip_header = ('version', 'type', 'length', 'id', 'flags', 'ttl', 'protocol', 'checksum', 'src_ip')
	return dict(zip(ip_header, struct.unpack("!BBHHHBBHII", packet[:20])))

def _calc_delay(send_time, receive_time):
	if not send_time or not receive_time:
		return -1
	return (receive_time - send_time)*1000

def _echo_message(message):
	print(message)

def _wait_until_next(delay, max_wait):
	if max_wait > delay:
		time.sleep((max_wait - delay)/1000)

def make_socket(is_udp, is_bind, is_ipv6):

	if is_ipv6:
		sock_af = socket.AF_INET6
		sock_protocol = socket.getprotobyname("ipv6-icmp")
		if is_udp:
			sock_type = socket.SOCK_DGRAM
		else:
			sock_type = socket.SOCK_RAW
	else:
		sock_af = socket.AF_INET
		sock_protocol = socket.getprotobyname("icmp")
		if is_udp:
			sock_type = socket.SOCK_DGRAM
		else:
			sock_type = socket.SOCK_RAW
	try:
		my_socket = socket.socket(sock_af, sock_type, sock_protocol)

	except:
		my_socket = -1

	return my_socket
	'''
	if is_bind:
		my_socket.bind((self.bind, 0))
	'''

def make_packet(own_id, seq_num, is_ipv6):
	# Header is type (8), code (8), checksum (16), id (16), sequence (16)
	checksum = 0

	# Make a dummy header with a 0 checksum
	if is_ipv6:
		header = struct.pack(
			"!BbHHh", ICMP_ECHO_IPV6, 0, checksum,
				own_id, seq_num)
	else:
		header = struct.pack(
			"!BBHHH", ICMP_ECHO_CONST, 0, checksum,
			own_id, seq_num)

	#B - Unsigned Char (8 bits)
	#H - Unsigned Short (16 bits)
	'''
    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |     ICMP_ECHO  |     0        |          checksum             |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                own_id         |             seq_number        |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
	'''
	pad_bytes = []
	# Annotation: 0x42 = 66 decimal
	start_val = 0x42
	for i in range(start_val, start_val + (PACKET_SIZE_CONST-8)):
		pad_bytes += [(i & 0xff)]  # Keep chars in the 0-255 range
	data = bytearray(pad_bytes)
	# b'BCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwx'
	checksum = _checksum(header + data)

	if is_ipv6:
		header = struct.pack(
			"!BbHHh", ICMP_ECHO_IPV6, 0, checksum,
				own_id, seq_num)
	else:
		header = struct.pack(
			"!BBHHH", ICMP_ECHO_CONST, 0, checksum,
			own_id, seq_num)

	return header + data

def send(my_socket, dest, own_id, seq_num, is_ipv6):
	packet = make_packet(own_id, seq_num, is_ipv6)
	send_time = timer()
	if is_ipv6:
		my_socket.sendto(packet, (dest, ICMP_PORT_IPV6, 0, 0))
		raise Exception({send_time})
	else:
		my_socket.sendto(packet, (dest, ICMP_PORT))
	return send_time

def receive(my_socket, own_id):

	timeout = TIMEOUT_CONST / 1000
	while True:
		select_start = timer()
		inputready, outputready, exceptready = select.select([my_socket], [], [], timeout)
		select_duration = (timer() - select_start)
		if inputready == []:
			return 0, 0, 0, None, None

		packet, address = my_socket.recvfrom(ICMP_MAX_RECV_CONST)
		icmp_header = _parse_icmp_header(packet)

		receive_time = timer()
		if icmp_header["packet_id"] == own_id: # my packet
			ip_header = _parse_ip_header(packet)
			ip = socket.inet_ntoa(struct.pack("!I", ip_header["src_ip"]))
			packet_size = len(packet) - 28
			return receive_time, packet_size, ip, ip_header, icmp_header

		timeout = timeout - select_duration

		if timeout <= 0:
			return 0, 0, 0, None, None

def ping(dest, times=1, msg_imp = 0):
	ipv6 = False
	f_msg_imp = ""
	try:
		dest_ip = _to_ip(dest,ipv6)
	except socket.gaierror:
		msg = "ping: cannnot resolve {}: Unknown host".format(dest)
		if(msg_imp):
			f_msg_imp += msg
		_echo_message(msg)
		return -1, -1, f_msg_imp

	if not dest_ip:
		return -1, -1, f_msg_imp

	seq_num = 0
	# create socket to send it
	try:
		my_socket = make_socket(None, None, ipv6)
	except socket.error as e:
		etype, evalue, etb = sys.exc_info()
		if e.errno == 1:
			# Operation not permitted - Add more information to traceback
			msg = "{} - Note that ICMP messages can only be send from processes running as root.".format(evalue)
			if(msg_imp):
				f_msg_imp += msg
		else:
			msg = str(evalue)
		_echo_message(msg)
		return -2, -2, f_msg_imp

	own_id = os.getpid() & 0xFFFF
	delay = 0
	timeout = 0
	
	for i in range(0, times):
		try:
			send_time = send(my_socket, dest_ip, own_id, seq_num, ipv6)
		except socket.error as e:
			msg = "General failure ({})".format(e.args[1])
			if(msg_imp):
				f_msg_imp += msg
			_echo_message(msg)
			my_socket.close()
			return -2, -2, f_msg_imp

		if not send_time:
			return -1, -1, f_msg_imp

		receive_time, packet_size, ip, ip_header, icmp_header = receive(my_socket, own_id)

		delay = _calc_delay(send_time, receive_time)

		# if receive_time value is 0, it means packet could not received
		if receive_time == 0:
			msg = "\n{} -- Request timeout".format(dest)
			timeout += 1
			_echo_message(msg)
			if(msg_imp):
				f_msg_imp += msg

		else:
			msg = "{} -- {} bytes from {}: icmp_seq={} ttl={} time={:.3f} ms".format(
				dest,
				packet_size,
				ip,
				seq_num,
				ip_header['ttl'],
				delay
			)	
			_echo_message(msg)
			if(msg_imp):
				f_msg_imp += msg + "\n"

		seq_num += 1
		_wait_until_next(delay, MAX_WAIT)

	my_socket.close()

	return delay, timeout, f_msg_imp
