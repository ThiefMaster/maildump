import './jquery-stub';
import 'jquery.hotkeys';
import './util';
import './message';

(function($) {
    'use strict';

    let online = true;

    let evtSource = null;
    const waitForEvents = (events, states) => {
        evtSource = new EventSource('/event-stream');
        let wasConnected = false;

        evtSource.onopen = () => {
            wasConnected = true;
            states.connected();
        };
        evtSource.onerror = evt => {
            if (wasConnected) {
                states.disconnected();
            }
            if (evt.target.readyState === EventSource.CLOSED) {
                setTimeout(() => {
                    waitForEvents(events, states);
                }, 1000);
            }
        };
        evtSource.onmessage = evt => console.log(evt.data);
        Object.entries(events).forEach(([evt, cb]) => {
            evtSource.addEventListener(evt, e => {
                cb(e.data);
            });
        })
    };

    $(document).ready(function() {
        // Misc stuff and initialization
        $('.resizer').on('mousedown', function(e) {
            if(e.button != 0) {
                return;
            }
            var $this = $(this);
            var target = $this.data('sibling') == 'prev' ? $this.prev() : $this.next();
            e.preventDefault();
            $(document).on('mousemove.resizer', function(e) {
                e.preventDefault();
                target.css('height', e.clientY - target.offset().top);
            }).on('mouseup.resizer', function(e) {
                e.preventDefault();
                $(document).off('.resizer');
            });
        });

        // Top nav actions
        $('nav.app .quit a').on('click', function(e) {
            e.preventDefault();
            if(!confirm('Do you really want to terminate the MailDump application?')) {
                return;
            }
            restCall('DELETE', '/');
        });

        $('nav.app .clear a').on('click', function(e) {
            e.preventDefault();
            if (!confirm('Do you really want to delete all messages?')) {
                return;
            }
            restCall('DELETE', '/messages/');
        });

        if (NotificationUtil.available) {
            var notificationButton = $('nav.app .notifications a');

            var updateNotificationButton = function updateNotificationButton() {
                const enabled = localStorage.getItem('notifications') === 'true' && NotificationUtil.checkPermission();
                notificationButton.text(enabled ? 'Disable notifications' : 'Enable notifications');
            };

            notificationButton.parent().show();
            notificationButton.on('click', function(e) {
                e.preventDefault();
                switch (NotificationUtil.checkPermission()) {
                    case false: // denied
                        alert('You need to allow notifications via site permissions.');
                        return;
                    case true: // allowed
                        localStorage.setItem('notifications', localStorage.getItem('notifications') !== 'true');
                        updateNotificationButton();
                        break;
                    default: // not specified (prompt user)
                        NotificationUtil.requestPermission(function(perm) {
                            localStorage.setItem('notifications', !!perm);
                            updateNotificationButton();
                        });
                        break;

                }
            });
            updateNotificationButton();
        }

        $('#search').on('keyup', function() {
            var term = $(this).val().trim().toLowerCase();
            Message.applyFilter(term);
        });

        // Message navigation
        $('#messages').on('click', '> tr:not(.deleted)', function(e) {
            var msg;
            if (e.ctrlKey) {
                msg = Message.getSelected();
                if (msg) {
                    msg.deselect();
                }
                if (window.getSelection) {
                    window.getSelection().removeAllRanges();
                }
            }
            else {
                msg = Message.get($(this).data('messageId'));
                if (msg && msg != Message.getSelected()) {
                    msg.select();
                    $('#message').show();
                }
            }
        });

        $('.tab.format').on('click', function(e) {
            e.preventDefault();
            var msg = Message.getSelected();
            if (msg) {
                $('.tab.format.selected').removeClass('selected');
                $(this).addClass('selected');
                msg.updateFormat();
            }
        });

        $('.action.delete').on('click', function(e) {
            e.preventDefault();
            var msg = Message.getSelected();
            if (msg) {
                msg.delRemote();
            }
        });

        let terminating = false;
        window.onbeforeunload = function() {
            terminating = true;
            if (evtSource) {
                evtSource.close();
            }
            Message.closeNotifications()
        };

        // Real-time updates
        waitForEvents({
            add_message: id => {
                console.log('SSE: received new message', id);
                Message.load(+id, localStorage.getItem('notifications') === 'true');
            },
            delete_message: id => {
                console.log('SSE: deleted message', id);
                const msg = Message.get(+id);
                if (msg) {
                    msg.del();
                }
            },
            delete_messages: () => {
                console.log('SSE: deleted all emssages');
                Message.deleteAll();
            }
        }, {
            connected: () => {
                console.log('SSE: connected');
                online = true;
                document.body.classList.remove('disconnected');
                Message.loadAll();
            },
            disconnected: () => {
                console.log('SSE: disconnected');
                if (terminating) {
                    return;
                }
                document.body.classList.add('disconnected');
                online = false;
            }
        })

        // Keyboard shortcuts
        registerHotkeys({
            'del': function() {
                var msg = Message.getSelected();
                if (msg) {
                    msg.delRemote();
                }
            },
            'backspace': function(e) {
                // Backspace causing the iframe to go back even if it's not focused is annoying!
                e.preventDefault();
            },
            'f5': function() {
                // Chrome bug: http://stackoverflow.com/q/5971710/298479
                Message.closeNotifications();
            },
            'ctrl+f5': function() {
                // Chrome bug: http://stackoverflow.com/q/5971710/298479
                Message.closeNotifications();
            },
            'ctrl+r': function() {
                // Chrome bug: http://stackoverflow.com/q/5971710/298479
                Message.closeNotifications();
            },
            'up': function(e) {
                e.preventDefault();
                var msg = Message.getSelected();
                if (!msg) {
                    $('#messages > tr:last').trigger('click');
                    return;
                }
                msg.dom().prevAll(':visible').first().trigger('click');
            },
            'down': function(e) {
                e.preventDefault();
                var msg = Message.getSelected();
                if (!msg) {
                    $('#messages > tr:first').trigger('click');
                    return;
                }
                msg.dom().nextAll(':visible').first().trigger('click');
            },
            'ctrl+up': function(e) {
                e.preventDefault();
                $('#messages > tr:first').trigger('click');
            },
            'ctrl+down': function(e) {
                e.preventDefault();
                $('#messages > tr:last').trigger('click');
            },
            '/': function(e) {
                e.preventDefault();
                $('#search').focus();
            }
        }, () => online);
    });
})(jQuery);
