from django.db import models
from django import forms
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from urllib2 import urlopen
from urllib import urlencode
from hashlib import sha1
import xml.etree.ElementTree as ET
import random

def parse(response):
    try:
        xml = ET.XML(response)
        code = xml.find('returncode').text
        if code == 'SUCCESS':
            return xml
        else:
            raise
    except:
        return None

class Meeting(models.Model):

    name = models.CharField(max_length=100, unique=True, verbose_name=_('meeting name'))
    meeting_id = models.CharField(max_length=100, unique=True, verbose_name=_('meeting id'))
    attendee_password = models.CharField(max_length=50, verbose_name=_('attendee password'))
    moderator_password = models.CharField(max_length=50, verbose_name=_('moderator password'))

    @classmethod
    def api_call(self, query, call):
        prepared = "%s%s%s" % (call, query, settings.SALT)
        checksum = sha1(prepared).hexdigest()
        result = "%s&checksum=%s" % (query, checksum)
        return result

    def is_running(self):
        call = 'isMeetingRunning'
        query = urlencode((
            ('meetingID', self.meeting_id),
        ))
        hashed = self.api_call(query, call)
        url = settings.BBB_API_URL + call + '?' + hashed
        result = parse(urlopen(url).read())
        if result:
            return result.find('running').text
        else:
            return 'error'

    @classmethod
    def end_meeting(self, meeting_id, password):
        call = 'end'
        query = urlencode((
            ('meetingID', meeting_id),
            ('password', password),
        ))
        hashed = self.api_call(query, call)
        url = settings.BBB_API_URL + call + '?' + hashed
        result = parse(urlopen(url).read())
        if result:
            pass
        else:
            return 'error'

    @classmethod
    def meeting_info(self, meeting_id, password):
        call = 'getMeetingInfo'
        query = urlencode((
            ('meetingID', meeting_id),
            ('password', password),
        ))
        hashed = self.api_call(query, call)
        url = settings.BBB_API_URL + call + '?' + hashed
        r = parse(urlopen(url).read())
        if r:
            # Create dict of values for easy use in template
            d = {
                'start_time': r.find('startTime').text,
                'end_time': r.find('endTime').text,
                'participant_count': r.find('participantCount').text,
                'moderator_count': r.find('moderatorCount').text,
                'moderator_pw': r.find('moderatorPW').text,
                'attendee_pw': r.find('attendeePW').text,
                'invite_url': reverse('join', args=[meeting_id]),
            }
            return d
        else:
            return None

    @classmethod
    def get_meetings(self):
        call = 'getMeetings'
        query = urlencode((
            ('random', 'random'),
        ))
        hashed = self.api_call(query, call)
        url = settings.BBB_API_URL + call + '?' + hashed
        result = parse(urlopen(url).read())
        if result:
            # Create dict of values for easy use in template
            d = []
            r = result[1].findall('meeting')
            for m in r:
                meeting_id = m.find('meetingID').text
                password = m.find('moderatorPW').text
                d.append({
                    'name': meeting_id,
                    'running': m.find('running').text,
                    'moderator_pw': password,
                    'attendee_pw': m.find('attendeePW').text,
                    'info': Meeting.meeting_info(
                        meeting_id,
                        password)
                })
                print d
            return d
        else:
            return 'error'

    def start(self):
        call = 'create' 
        voicebridge = 70000 + random.randint(0,9999)
        query = urlencode((
            ('name', self.name),
            ('meetingID', self.meeting_id),
            ('attendeePW', self.attendee_password),
            ('moderatorPW', self.moderator_password),
            ('voiceBridge', voicebridge),
            ('welcome', "Welcome!"),
        ))
        hashed = self.api_call(query, call)
        url = settings.BBB_API_URL + call + '?' + hashed
        print url
        result = parse(urlopen(url).read())
        if result:
            return result
        else:
            raise

    @classmethod
    def join_url(self, meeting_id, name, password):
        call = 'join'
        query = urlencode((
            ('fullName', name),
            ('meetingID', meeting_id),
            ('password', password),
        ))
        hashed = self.api_call(query, call)
        url = settings.BBB_API_URL + call + '?' + hashed
        return url

    class CreateForm(forms.Form):
        name = forms.SlugField(label=_('meeting name'))
        attendee_password = forms.CharField(label=_('attendee password'),
            widget=forms.PasswordInput(render_value=False))
        moderator_password= forms.CharField(label=_('moderator password'),
            widget=forms.PasswordInput(render_value=False))

        def clean(self):
            data = self.cleaned_data

            # TODO: should check for errors before modifying
            data['meeting_id'] = data.get('name')

            if Meeting.objects.filter(name = data.get('name')):
                raise forms.ValidationError("That meeting name is already in use")
            return data

    class JoinForm(forms.Form):
        name = forms.CharField(label=_("Your name"))
        password = forms.CharField(label=_('password'),
            widget=forms.PasswordInput(render_value=False))
