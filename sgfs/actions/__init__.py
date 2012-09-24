import platform
from subprocess import call


def notify(msg):
    print msg
    if platform.system() == 'Darwin':
        call(['growlnotify', '-t', 'SGFS', '-m', msg])
    else:
        call(['notify-send', msg])
