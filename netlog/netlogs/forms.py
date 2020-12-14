from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from netlogs.models import Hosts, HostUsersMonitor, PortMonitor


User = get_user_model()


class UserSignUpForm(UserCreationForm):
	class Meta(UserCreationForm.Meta):
		model = User
		fields = ('username', 'email', 'first_name', 'surname','last_name')

	def __init__(self, *args, **kwargs):
		super(UserSignUpForm, self).__init__(*args, **kwargs)

		for key in self.fields:
			self.fields[key].required = True 
			self.fields[key].widget.attrs.update({
				'class': 'form-control',
				'step': '0.1'
			})

	def save(self, commit=True):
		user = super().save(commit=False)
		if commit:
			user.save()
		return user

class UserForm(forms.ModelForm):
	class Meta:
		model = User
		fields = ('username', 'email', 'first_name', 'surname','last_name')

	def __init__(self, *args, **kwargs):
		super(UserForm, self).__init__(*args, **kwargs)

		for name in self.fields.keys():
			self.fields[name].widget.attrs.update({
				'class': 'form-control',
				'step': '0.1'
			})

class HostsForm(forms.ModelForm):
	class Meta:
		model = Hosts
		fields = ('name',)

	def __init__(self, *args, **kwargs):
		super(HostsForm, self).__init__(*args, **kwargs)

		for name in self.fields.keys():
			self.fields[name].widget.attrs.update({
				'class': 'form-control',
				'step': '0.1'
			})



class HostUsersMonitorForm(forms.ModelForm):
	class Meta:
		model = HostUsersMonitor
		fields = ('end_time',)


	def __init__(self, *args, **kwargs):
		super(HostUsersMonitorForm, self).__init__(*args, **kwargs)

		for name in self.fields.keys():
			self.fields[name].widget.attrs.update({
				'class': 'form-control',
				'step': '0.1',
				'autocomplete': 'off',
				'id': 'datetimepicker'
			})


class PortMonitorForm(forms.ModelForm):
	class Meta:
		model = PortMonitor
		fields = ('ports','protocol','end_time',)


	def __init__(self, *args, **kwargs):
		super(PortMonitorForm, self).__init__(*args, **kwargs)

		self.fields['end_time'].widget.attrs.update({
			'class': 'form-control',
			'autocomplete': 'off',
			'step': '0.1',
				'id': 'datetimepicker'
		})

		self.fields['ports'].widget.attrs.update({
			'class': 'form-control',
			'step': '0.1',
			'placeholder': 'Ports (ex: 80, 8080, 25, 21)',
		})

		self.fields['protocol'].widget.attrs.update({
			'class': 'form-control',
			'step': '0.1',
		})