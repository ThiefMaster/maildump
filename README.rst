MailDump
========

MailDump is a python-based clone of the awesome `MailCatcher`_ tool. Its
purpose is to provide developers a way to let applications send emails
without actual emails being sent to anyone. Additionally lazy developers
might prefer this over a real SMTP server simply for the sake of it
being much easier and faster to set up.

Installation
------------

1. `git clone https://github.com/ThiefMaster/maildump.git`
2. `cd maildump`
3. `pip install -r requirements.txt`
4. `python setup.py build`
5. `python setup.py install`
6. `maildump`

Point your application's SMTP settings to port 1025 on EMAIL_HOST = '127.0.0.1'

If you are using Django, you can add these settings to your settings.py file::

    if DEBUG:
        EMAIL_HOST = '127.0.0.1'
        EMAIL_PORT = 1025
        EMAIL_HOST_USER = ''
        EMAIL_HOST_PASSWORD = ''
        EMAIL_USE_TLS = False

Usage
-----

Open your web browser and go to http://127.0.0.1:1080

Features
--------

Since the goal of this project is to have the same features as
MailCatcher I suggest you to read its readme instead.

However, there is one unique feature in MailDump: Password protection for
the web interface. If your MailDump instance is listening on a public IP
you might not want your whole company to have access to it. Instead you can
use an Apache-style htpasswd file. I have tested it with SHA-encrypted
passwords but you can use any encryption supported by `passlib.apache`_.

Credits
-------

The layout of the web interface has been taken from MailCatcher. No
Copy&Paste involved - I rewrote the SASS/Compass stylesheet from
MailCatcher in SCSS as there is a pure-python implementation of SCSS
available. If whoever reads this feels like creating a new layout that
looks as good or even better feel free to send a pull request. I'd
actually prefer a layout that differs from MailCatcher at least a little
bit but I'm somewhat bad at creating layouts!

The icon was created by `Tobia Crivellari`_.

License
-------

Copyright © 2013-2015 Adrian Mönnich (adrian@planetcoding.net). Released
under the MIT License, see `LICENSE`_ for details.

.. _MailCatcher: https://github.com/sj26/mailcatcher/blob/master/README.md
.. _passlib.apache: http://pythonhosted.org/passlib/lib/passlib.apache.html
.. _Tobia Crivellari: http://dribbble.com/TobiaCrivellari
.. _LICENSE: https://github.com/ThiefMaster/maildump/blob/master/LICENSE
