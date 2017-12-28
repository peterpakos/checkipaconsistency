#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tool to check consistency across FreeIPA servers

Author: Peter Pakos <peter.pakos@wandisco.com>

Copyright (C) 2017 WANdisco

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import absolute_import, print_function
import os
import sys
import argparse
from prettytable import PrettyTable
import dns.resolver
from collections import OrderedDict

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

from . import VERSION
from .logger import get_logger
from .freeipaserver import FreeIPAServer


class Checks(object):
    def __init__(self):
        pass


class Main(object):
    VERSION = VERSION

    def __init__(self):
        self._app_name = os.path.basename(sys.modules['__main__'].__file__)
        self._app_dir = os.path.dirname(os.path.realpath(__file__))
        self._parse_args()
        self._log = get_logger(debug=self._args.debug, quiet=self._args.quiet,
                               file_level='DEBUG' if self._args.log_file else False,
                               log_file=self._args.log_file if self._args.log_file else False)
        self._log.debug(self._args)
        self._log.debug('Initialising...')

        self._domain = None
        self._hosts = []
        self._binddn = 'cn=Directory Manager'
        self._bindpw = None

        self._load_config()

        if self._args.domain:
            self._log.debug('Domain set by argument')
            self._domain = self._args.domain

        if not self._domain:
            self._log.critical('IPA domain not set')
            exit(1)
        else:
            self._log.debug('IPA domain: %s' % self._domain)

        if self._args.hosts:
            self._log.debug('Server list set by argument')
            self._hosts = self._args.hosts

        for i, host in enumerate(self._hosts):
            if not host or ' ' in host:
                self._log.critical('Incorrect server name: %s' % host)
                exit(1)

        if not self._hosts:
            self._log.debug('Searching for IPA servers in DNS')
            record = '_ldap._tcp.%s' % self._domain
            answers = []

            try:
                answers = dns.resolver.query(record, 'SRV')
            except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
                self._log.critical('IPA servers not set, also failed to find any in DNS')
                exit(1)

            for answer in answers:
                self._hosts.append(str(answer).split(' ')[3].rstrip('.'))

        self._log.debug('IPA servers: %s' % ', '.join(self._hosts))

        if self._args.binddn:
            self._log.debug('Bind DN set by argument')
            self._binddn = self._args.binddn

        if not self._binddn:
            self._log.critical('Bind DN not set')
            exit(1)

        if self._args.bindpw:
            self._log.debug('Bind password set by argument')
            self._bindpw = self._args.bindpw

        if not self._bindpw:
            self._log.critical('Bind password not set')
            exit(1)

        self._servers = OrderedDict()
        for host in self._hosts:
            self._servers[host] = FreeIPAServer(host, self._domain, self._binddn, self._bindpw)

        self._checks = OrderedDict([
            ('users', 'Active Users'),
            ('susers', 'Stage Users'),
            ('pusers', 'Preserved Users'),
            ('hosts', 'Hosts'),
            ('services', 'Services'),
            ('ugroups', 'User Groups'),
            ('hgroups', 'Host Groups'),
            ('ngroups', 'Netgroups'),
            ('hbac', 'HBAC Rules'),
            ('sudo', 'SUDO Rules'),
            ('zones', 'DNS Zones'),
            ('certs', 'Certificates'),
            ('conflicts', 'LDAP Conflicts'),
            ('ghosts', 'Ghost Replicas'),
            ('bind', 'Anonymous BIND'),
            ('msdcs', 'Microsoft ADTrust'),
            ('replicas', 'Replication Status')
        ])

    def _parse_args(self):
        parser = argparse.ArgumentParser(description='Tool to check consistency across FreeIPA servers', add_help=False)
        parser.add_argument('-H', '--hosts', nargs='*', dest='hosts', help='list of IPA servers')
        parser.add_argument('-d', '--domain', nargs='?', dest='domain', help='IPA domain')
        parser.add_argument('-D', '--binddn', nargs='?', dest='binddn', help='Bind DN (default: cn=Directory Manager)')
        parser.add_argument('-W', '--bindpw', nargs='?', dest='bindpw', help='Bind password')
        parser.add_argument('--help', action='help', help='show this help message and exit')
        parser.add_argument('--version', action='version',
                            version='%s %s' % (os.path.basename(sys.argv[0]), self.VERSION))
        parser.add_argument('--debug', action='store_true', dest='debug', help='debugging mode')
        parser.add_argument('--quiet', action='store_true', dest='quiet', help='do not log to console')
        parser.add_argument('-l', '--log-file', nargs='?', dest='log_file', default='not_set',
                            help='log to file (./%s.log by default)' % self._app_name)
        parser.add_argument('--no-header', action='store_true', dest='disable_header', help='disable table header')
        parser.add_argument('--no-border', action='store_true', dest='disable_border', help='disable table border')
        parser.add_argument('-n', nargs='?', dest='nagios_check', help='Nagios plugin mode', default='not_set',
                            choices=['', 'all', 'users', 'susers', 'pusers', 'hosts', 'services', 'ugroups', 'hgroups',
                                     'ngroups', 'hbac', 'sudo', 'zones', 'certs', 'conflicts', 'ghosts', 'bind',
                                     'msdcs', 'replicas'])
        parser.add_argument('-w', '--warning', type=int, dest='warning',
                            default=1, help='number of failed checks before warning (default: %(default)s)')
        parser.add_argument('-c', '--critical', type=int, dest='critical',
                            default=2, help='number of failed checks before critical (default: %(default)s)')

        args = parser.parse_args()

        if args.log_file == 'not_set':
            args.log_file = None
        elif not args.log_file:
            args.log_file = self._app_name + '.log'

        if args.nagios_check == 'not_set':
            args.nagios_check = None
        elif not args.nagios_check:
            args.nagios_check = 'all'

        self._args = args

    def _load_config(self):
        config = configparser.ConfigParser()
        file_dir = os.path.expanduser(os.environ.get('XDG_CONFIG_HOME', '~/.config'))

        if not os.path.exists(file_dir):
            self._log.debug('Config directory %s does not exist, creating' % file_dir)
            os.makedirs(file_dir)

        config_file = os.path.join(
            file_dir,
            os.path.splitext(__name__)[0]
        )

        if not os.path.isfile(config_file):
            self._log.debug('Config file not found at %s' % config_file)
            config.add_section('IPA')
            config.set('IPA', 'DOMAIN', 'ipa.example.com')
            config.set('IPA', 'HOSTS', 'ipa01, ipa02, ipa03, ipa04, ipa05, ipa06')
            config.set('IPA', 'BINDDN', 'cn=Directory Manager')
            config.set('IPA', 'BINDPW', 'example123')
            with open(config_file, 'w') as cfgfile:
                config.write(cfgfile)
            self._log.info('Initial config saved to %s - PLEASE EDIT IT!' % config_file)
            return

        self._log.debug('Loading configuration file %s' % config_file)

        if 'example' in open(config_file).read():
            self._log.debug('Initial config found in %s - PLEASE EDIT IT!' % config_file)
            return

        config.read(config_file)

        if not config.has_section('IPA'):
            self._log.debug('Config file has no IPA section')
            return

        if config.has_option('IPA', 'DOMAIN'):
            self._domain = config.get('IPA', 'DOMAIN')
            self._log.debug('DOMAIN = %s' % self._domain)
        else:
            self._log.debug('IPA.DOMAIN not set')

        if config.has_option('IPA', 'HOSTS'):
            self._hosts = config.get('IPA', 'HOSTS')
            self._log.debug('HOSTS = %s' % self._hosts)
            self._hosts = self._hosts.replace(',', ' ').split()
        else:
            self._log.debug('IPA.SERVERS not set')

        if config.has_option('IPA', 'BINDDN'):
            self._binddn = config.get('IPA', 'BINDDN')
            self._log.debug('BINDDN = %s' % self._binddn)
        else:
            self._log.debug('IPA.BINDDN not set')

        if config.has_option('IPA', 'BINDPW'):
            self._bindpw = config.get('IPA', 'BINDPW')
            self._log.debug('BINDPW = ********')
        else:
            self._log.debug('IPA.BINDPW not set')

    def run(self):
        self._log.debug('Starting...')
        if self._args.nagios_check:
            self._log.debug('Nagios plugin mode')
            self._nagios_plugin(self._args.nagios_check)
        else:
            self._log.debug('CLI mode')
            self._print_table()
        self._log.debug('Finishing...')

    def _print_table(self):
        table = PrettyTable(
            ['FreeIPA servers:'] + [getattr(server, 'hostname_short') for server in self._servers.values()] + ['STATE'],
            header=not self._args.disable_header,
            border=not self._args.disable_border
        )
        table.align = 'l'

        for check in self._checks:
            state = 'OK' if self._is_consistent(check, [getattr(server, check) for server in self._servers.values()])\
                else 'FAIL'
            table.add_row(
                [self._checks[check]] +
                [getattr(server, check) for server in self._servers.values()] +
                [state]
            )

        self._log.info(table)

    def _is_consistent(self, check, check_results):
        if check == 'conflicts':
            conflicts = [getattr(server, 'conflicts') for server in self._servers.values()]
            if conflicts.count(conflicts[0]) == len(conflicts) and conflicts[0] == 0:
                return True
            else:
                return False
        elif check == 'ghosts':
            ghosts = [getattr(server, 'ghosts') for server in self._servers.values()]
            if ghosts.count(ghosts[0]) == len(ghosts) and ghosts[0] == 0:
                return True
            else:
                return False
        elif check == 'replicas':
            healths = [getattr(server, 'healthy_agreements') for server in self._servers.values()]
            if healths.count(healths[0]) == len(healths) and healths[0]:
                return True
            else:
                return False
        if check_results.count(check_results[0]) == len(check_results) and None not in check_results:
            return True
        else:
            return False

    def _nagios_plugin(self, check):
        self._log.debug('Running check: %s' % check)
        if check == 'all':
            checks_no = len(self._checks)
            oks = 0
            for check in self._checks:
                if self._is_consistent(check, [getattr(server, check) for server in self._servers.values()]):
                    oks += 1
            fails = checks_no - oks
            if 0 <= fails < self._args.warning:
                msg = 'OK'
                code = 0
            elif self._args.warning <= fails < self._args.critical:
                msg = 'WARNING'
                code = 1
            elif fails >= self._args.critical:
                msg = 'CRITICAL'
                code = 2
            else:
                msg = 'UNKNOWN'
                code = 3
            self._log.info('%s - %s/%s checks passed' % (msg, oks, checks_no))
            exit(code)
        else:
            if self._is_consistent(check, [getattr(server, check) for server in self._servers.values()]):
                msg = 'OK'
                code = 0
            else:
                msg = 'CRITICAL'
                code = 2
            self._log.info('%s - %s' % (msg, self._checks[check]))
            exit(code)


def main():
    try:
        Main().run()
    except KeyboardInterrupt:
        print('\nTerminating...')
        exit(130)
