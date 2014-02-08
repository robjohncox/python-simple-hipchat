Simple Python HipChat
=====================

Description
-----------
Wrapper around the HipChat API.

Big shout out to **kurttheviking** who wrote the original version of this library (which this version was
forked from). This library is heavily based on his original code, this version adds a bunch of wrapper functions
for getting rooms and users, and also adds object wrappers around room and user data.

**Important Note:** This has has basic testing so far, but is not yet extensively tested, so bound to be a
couple of bugs in here.

Dependencies
------------
None beyond the Python standard library.

Usage
-----

Install::

    pip install https://github.com/robjohncox/python-simple-hipchat

Instantiate::

    import hipchat
    hipster = HipChat(token=YourHipChatToken)

Create and Lookup Rooms::

    all_rooms = hipster.get_rooms()
    room = hipster.get_room_by_name('My Room')
    room = hipster.get_room_by_id(123456)
    new_room = hipster.create_room('New Room', owner, topic='General Chit-Chat', private=True)

Selected Room Attributes::

    room.id
    room.name
    room.topic
    room.members
    room.participants

Selected Room Functions::

    room.send_message('Support Bot', 'There is a problem', notify=True)
    room.change_topic('Lets talk about something different')
    room.delete()

Lookup Users::

    all_users = hipster.get_users()
    user = hipster.get_user_by_name('Carol')
    user = hipster.get_user_by_id(123456)

Selected User Attributes::

    user.id
    user.name
    user.mention_name
    user.title
    user.status

Raw API Access::

    hipster.method(url='method/url/', method="GET/POST", parameters={'name':'value', })
    hipster.method('rooms/message', method='POST', parameters={'room_id': 8675309, 'from': 'HAL', 'message': 'All your base...'})
