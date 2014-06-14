#!/usr/bin/python
"""Set Foodsoft admin password, email and variant

Option:
    --pass=     unless provided, will ask interactively
    --email=    unless provided, will ask interactively
    --variant=  unless provided, will ask interactively

"""

import os
import sys
import glob
import getopt
import string
import subprocess
from subprocess import Popen, PIPE

from dialog_wrapper import Dialog

APPS_PATH='/var/www/'
APP_DEFAULT_PATH=os.path.join(APPS_PATH, 'foodsoft')

def quote(s):
    return "'" + s.replace("'", "\\'") + "'"

def usage(s=None):
    if s:
        print >> sys.stderr, "Error:", s
    print >> sys.stderr, "Syntax: %s [options]" % sys.argv[0]
    print >> sys.stderr, __doc__
    sys.exit(1)

def foodsoft_variant_desc(variant):
    desc = ''
    # figure out name
    if variant=='foodsoft-standard':
      desc = 'Standard version'
    else:
      desc = "Derivative '%s'" % variant.replace('foodsoft-', '')
    # append version
    try:
        version = open(os.path.join(APPS_PATH, variant, 'VERSION')).read().strip()
        desc += ' (v%s)' % version
    except IOError:
        pass
    return desc

def main():
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:], "h",
                                       ['help', 'pass=', 'email=', 'variant='])
    except getopt.GetoptError, e:
        usage(e)

    password = ""
    email = ""
    variant = ""
    for opt, val in opts:
        if opt in ('-h', '--help'):
            usage()
        elif opt == '--pass':
            password = val
        elif opt == '--email':
            email = val
        elif opt == '--variant':
            variant = val

    if not password:
        d = Dialog('TurnKey Linux - First boot configuration')
        password = d.get_password(
            "Foodsoft Password",
            "Enter new password for the Foodsoft 'admin' account.")

    if not email:
        if 'd' not in locals():
            d = Dialog('TurnKey Linux - First boot configuration')

        email = d.get_email(
            "Foodsoft Email",
            "Enter email address for the Foodsoft 'admin' account.",
            "admin@foodcoop.test")


    variant_cur = os.path.basename(os.path.realpath(APP_DEFAULT_PATH))
    variant_avail = map(lambda d: os.path.basename(d), glob.glob(os.path.join(APPS_PATH, 'foodsoft-*')))
    if len(variant_avail) == 1:
        variant = variant_avail[0]
    elif not variant:
        if 'd' not in locals():
            d = Dialog('TurnKey Linux - First boot configuration')

        # put foodsoft-standard in front of the list
	variant_avail.insert(0, variant_avail.pop(variant_avail.index('foodsoft-standard')))
        # and give all of them titles
	choices = map(lambda c: [c, foodsoft_variant_desc(c)], variant_avail)

        variant = d.menu(
            "Foodsoft variant",
            "Select which version of Foodsoft you'd like to use.",
            choices=choices)

    print "Please wait ..."

    # need mysql running for these updates
    Popen(['service mysql status >/dev/null || service mysql start'], shell=True).wait()

    if variant_cur != variant:
	    # use chosen variant
	    os.unlink(APP_DEFAULT_PATH)
	    os.symlink(variant, APP_DEFAULT_PATH)
	    Popen('bundle exec /usr/local/bin/rake -s db:migrate', cwd=APP_DEFAULT_PATH, env={"RAILS_ENV": "production"}, shell=True).wait()
	    Popen('service apache2 status >/dev/null && service apache2 restart', shell=True).wait()
	    Popen('service foodsoft-workers restart', shell=True).wait()

    # initialize admin account from Rails console
    p = Popen('bundle exec /usr/bin/ruby', stdin=PIPE, cwd=APP_DEFAULT_PATH, env={"RAILS_ENV": "production"}, shell=True)
    p.stdin.write("""
      require './config/environment'
      User.find_by_nick('admin').update_attributes email: "+quote(email)+", password: "+quote(password)+"
    """)
    p.stdin.close()
    p.wait()


if __name__ == "__main__":
    main()

