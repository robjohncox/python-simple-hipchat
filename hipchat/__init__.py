try:
    from urllib.parse import urljoin
    from urllib.parse import urlencode
    import urllib.request as urlrequest
except ImportError:
    from urlparse import urljoin
    from urllib import urlencode
    import urllib2 as urlrequest
import json
import logging
from datetime import datetime


# TODO Smarter with timeouts
# TODO Need to track how many API calls we have left
# TODO Support API v2
# TODO Split across multiple files
# TODO Ability to specify protected rooms and users at login which blocks mutators on them

log = logging.getLogger('hipchat')


class _HipChatObject(object):

    def __init__(self, data, hipchat):
        self.data = data
        self.hipchat = hipchat

    def __getitem__(self, item):
        return self.data[item]

    def __repr__(self):
        return str(self.data)


class MessagePriority(object):
    message = 'green'
    warning = 'yellow'
    alert = 'red'


class MessageFormat(object):
    text = 'text'
    html = 'html'


class Room(_HipChatObject):

    def __init__(self, data, hipchat):
        super(Room, self).__init__(data, hipchat)
        self._fully_loaded = False
        self._deleted = False

    def refresh(self):
        if self.is_deleted:
            log.warn('Cannot refresh data for room {0} as it has been deleted'.format(self.name))
            return
        response = self.hipchat.method('rooms/show', method='GET', parameters={
            'room_id': self.id,
        })
        self.data = response['room']
        self._fully_loaded = True

    def _ensure_fully_loaded(self):
        if self.is_deleted:
            log.warn('Cannot refresh data for room {0} as it has been deleted'.format(self.name))
            return
        if not self._fully_loaded:
            self.refresh()

    def send_message(self, from_name, message, notify=False, color=MessagePriority.message, format=MessageFormat.text):
        log.info('Sending message from {0} to room {1}: {2}'.format(from_name, self.name, message))
        if self.is_deleted:
            log.warn('Cannot post message to room {0} as it has been deleted'.format(self.name))
            return
        self.hipchat.method('rooms/message', method='POST', parameters={
            'room_id': self.id,
            'from': from_name,
            'message': message,
            'message_format': format,
            'color': color,
            'notify': 1 if notify else 0
        })
        
        
    def send_table_message(self, from_name, data, header_row=True, notify=False, color=MessagePriority.message):
        # Table data should be a 2D iterable structure, with the outer level representing one row per entry
        if self.is_deleted:
            return

        def row(row_data, header):
            message = '<tr>'
            for cell_data in row_data:
                message += '<td>{0}{1}{2}</td>'.format('<b>' if header else '',
                                                       cell_data,
                                                       '</b>' if header else '')
            message += '</tr>'
            return message
            
        message = '<table>'
        for index, row_data in enumerate(data):
            header = (index is 0 and header_row)
            message += row(row_data, header)
        message += '</table>'

        self.send_message(from_name, message, notify=notify, color=color, format=MessageFormat.html)

    def send_list_message(self, from_name, data, notify=False, color=MessagePriority.message):
        # List data should be an iterable of list items
        if self.is_deleted:
            return

        message = '<ul>'
        for list_item in data:
            message += '<li>{0}</li>'.format(list_item)
        message += '</ul>'

        self.send_message(from_name, message, notify=notify, color=color, format=MessageFormat.html)

    def change_topic(self, topic):
        log.info('Changing topic for room {0} to {1}'.format(self.name, topic))
        if self.is_deleted:
            log.warn('Cannot change topic, room is deleted')
            return
        self.hipchat.method('rooms/topic', method='POST', parameters={
            'room_id': self.id,
            'topic': topic
        })

    def delete(self):
        log.info('Deleting room {0}'.format(self.name))
        if self.is_deleted:
            log.warn('Cannot delete room as it is already deleted')
            return
        self.hipchat.method('rooms/delete', method='POST', parameters={
            'room_id': self.id
        })
        self._deleted = True
        self.hipchat.get_rooms(force_refresh=True)

    @property
    def id(self):
        return self['room_id']

    @property
    def name(self):
        return self['name']

    @property
    def topic(self):
        return self['topic']

    @property
    def is_deleted(self):
        return self._deleted

    # TODO Get messages

    @property
    def last_active(self):
        if not self['last_active']:
            return None
        return datetime.fromtimestamp(self['last_active'])

    @property
    def created(self):
        return datetime.fromtimestamp(self['created'])

    @property
    def owner_id(self):
        return self['owner_user_id']

    @property
    def owner(self):
        return self.hipchat.get_user_by_id(self.owner_id)

    @property
    def is_archived(self):
        return self['is_archived']

    @property
    def is_private(self):
        return self['is_private']

    @property
    def xmpp_jid(self):
        return self['xmpp_jid']

    @property
    def guest_access_url(self):
        return self['guest_access_url'] if self['guest_access_url'] else None

    @property
    def member_ids(self):
        if self.is_deleted:
            return []
        elif not self.is_private:
            return [user.id for user in self.hipchat.get_users()]
        else:
            self._ensure_fully_loaded()
            return self['member_user_ids']

    @property
    def members(self):
        return [user for user in self.hipchat.get_users() if user.id in self.member_ids and not user.is_deleted]

    @property
    def participant_ids(self):
        if self.is_deleted:
            return []
        else:
            self._ensure_fully_loaded()
            return [user['user_id'] for user in self['participants']]

    @property
    def participants(self):
        return [user for user in self.hipchat.get_users() if user.id in self.participant_ids]

    def __unicode__(self):
        return 'HipChat Room {0}: {1}'.format(self.id, self.name)


API_URL_DEFAULT = 'https://api.hipchat.com/v1/'
FORMAT_DEFAULT = 'json'


class User(_HipChatObject):

    # TODO delete, undelete, update

    @property
    def id(self):
        return self['user_id']

    @property
    def name(self):
        return self['name']

    @property
    def mention_name(self):
        return self['mention_name']

    @property
    def email(self):
        return self['email']

    @property
    def title(self):
        return self['title']

    @property
    def photo_url(self):
        return self['photo_url']

    @property
    def last_active(self):
        if not self['last_active']:
            return None
        return datetime.fromtimestamp(self['last_active'])

    @property
    def created(self):
        return datetime.fromtimestamp(self['created'])

    @property
    def status(self):
        return self['status']

    @property
    def status_message(self):
        return self['status_message']

    @property
    def is_group_admin(self):
        return self['is_group_admin'] is 1

    @property
    def is_deleted(self):
        return self['is_deleted'] is 1

    def __unicode__(self):
        return 'User {0}: {1}'.format(self.id, self.data)


class HipChat(object):
    def __init__(self, token=None, url=API_URL_DEFAULT, format=FORMAT_DEFAULT):
        self.url = url
        self.token = token
        self.format = format
        self.opener = urlrequest.build_opener(urlrequest.HTTPSHandler())
        self._rooms = None
        self._users = None

    def get_rooms(self, force_refresh=False):
        if not self._rooms or force_refresh:
            response = self.method('rooms/list')
            self._rooms = [Room(data, self) for data in response['rooms']]
        return self._rooms

    def get_room_by_name(self, name, force_refresh=False):
        rooms = self.get_rooms(force_refresh=force_refresh)
        for room in rooms:
            if room.name == name:
                return room
        return None

    def get_room_by_id(self, id, force_refresh=False):
        rooms = self.get_rooms(force_refresh=force_refresh)
        for room in rooms:
            if room.id == id:
                return room
        return None

    def create_room(self, name, owner, private=False, topic='', guest_access=False):
        self.method('rooms/create', method='POST', parameters={
            'name': name,
            'owner_user_id': owner.id,
            'privacy': 'private' if private else 'public',
            'topic': topic,
            'guest_access': 1 if guest_access else 0
        })
        return self.get_room_by_name(name, force_refresh=True)

    def get_users(self):
        if not self._users:
            response = self.method('users/list')
            self._users = [User(data, self) for data in response['users']]
        return self._users

    def get_user_by_name(self, name):
        users = self.get_users()
        for user in users:
            if user.name == name:
                return user
        return None

    def get_user_by_id(self, id):
        users = self.get_users()
        for user in users:
            if user.id == id:
                return user
        return None

    class RequestWithMethod(urlrequest.Request):
        def __init__(self, url, data=None, headers={}, origin_req_host=None, unverifiable=False, http_method=None):
            urlrequest.Request.__init__(self, url, data, headers, origin_req_host, unverifiable)
            if http_method:
                self.method = http_method

        def get_method(self):
            if self.method:
                return self.method
            return urlrequest.Request.get_method(self)

    def method(self, url, method="GET", parameters=None, timeout=None):
        log.info('Making {0} request to {1} with parameters {2}'.format(method, url, parameters))
        method_url = urljoin(self.url, url)

        if method == "GET":
            if not parameters:
                parameters = dict()

            parameters['format'] = self.format
            parameters['auth_token'] = self.token

            query_string = urlencode(parameters)
            request_data = None
        else:
            query_parameters = dict()
            query_parameters['auth_token'] = self.token

            query_string = urlencode(query_parameters)

            if parameters:
                request_data = urlencode(parameters).encode('utf-8')
            else:
                request_data = None

        method_url = method_url + '?' + query_string
        log.debug('Method URL: {0}'.format(method_url))

        req = self.RequestWithMethod(method_url, http_method=method, data=request_data)
        response = self.opener.open(req, None, timeout)

        # TODO Check response status (failures, throttling)

        return json.loads(response.read().decode('utf-8'))
