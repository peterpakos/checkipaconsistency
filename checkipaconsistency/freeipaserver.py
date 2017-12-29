#  -*- coding: utf-8 -*-
"""
FreeIPA Server module

Author: Peter Pakos <peter.pakos@wandisco.com>

Copyright (C) 2017 WANdisco

This file is part of checkipaconsistency.

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

from __future__ import print_function
import logging
import ldap
import dns.resolver


class FreeIPAServer(object):
    def __init__(self, host, domain, binddn, bindpw):
        self._log = logging.getLogger()
        self._log.debug('Initialising FreeIPA server %s' % host)

        self.users = None
        self.susers = None
        self.pusers = None
        self.hosts = None
        self.services = None
        self.ugroups = None
        self.hgroups = None
        self.ngroups = None
        self.hbac = None
        self.sudo = None
        self.zones = None
        self.certs = None
        self.conflicts = None
        self.ghosts = None
        self.bind = None
        self.msdcs = None
        self.replicas = None
        self.healthy_agreements = False

        self._binddn = binddn
        self._bindpw = bindpw
        self._domain = domain
        self._url = 'ldaps://' + host
        self.hostname_short = host.replace('.%s' % domain, '')
        self._conn = self._get_conn()

        if not self._conn:
            return

        self._fqdn = self._get_fqdn()
        self.hostname_short = self._fqdn.replace('.%s' % domain, '')

        self._log.debug('FQDN: %s, short hostname: %s' % (self._fqdn, self.hostname_short))

        self._base_dn = 'dc=' + self._domain.replace('.', ',dc=')

        context = self._get_context()
        if self._base_dn != context:
            self._log.critical('Context mismatch: %s vs %s' % (self._base_dn, context))
            exit(1)

        self._active_user_base = 'cn=users,cn=accounts,' + self._base_dn
        self._stage_user_base = 'cn=staged users,cn=accounts,cn=provisioning,' + self._base_dn
        self._preserved_user_base = 'cn=deleted users,cn=accounts,cn=provisioning,' + self._base_dn
        self._groups_base = 'cn=groups,cn=accounts,' + self._base_dn

        self.users = self._count_users(user_base='active')
        self.susers = self._count_users(user_base='stage')
        self.pusers = self._count_users(user_base='preserved')
        self.hosts = self._count_hosts()
        self.services = self._count_services()
        self.ugroups = self._count_groups()
        self.hgroups = self._count_hostgroups()
        self.ngroups = self._count_netgroups()
        self.hbac = self._count_hbac_rules()
        self.sudo = self._count_sudo_rules()
        self.zones = self._count_dns_zones()
        self.certs = self._count_certificates()
        self.conflicts = self._count_ldap_conflicts()
        self.ghosts = self._ghost_replicas()
        self.bind = self._anon_bind()
        self.msdcs = self._ms_adtrust()
        self.replicas, self.healthy_agreements = self._replication_agreements()

    @staticmethod
    def _get_ldap_msg(e):
        msg = e
        if hasattr(e, 'message'):
            msg = e.message
            if 'desc' in e.message:
                msg = e.message['desc']
            elif hasattr(e, 'args'):
                msg = e.args[0]['desc']
        return msg

    def _get_conn(self):
        self._log.debug('Setting up LDAP connection')
        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

        try:
            conn = ldap.initialize(self._url)
            conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 3)
            conn.simple_bind_s(self._binddn, self._bindpw)
        except (
            ldap.SERVER_DOWN,
            ldap.NO_SUCH_OBJECT,
            ldap.INVALID_CREDENTIALS
        ) as e:
            if hasattr(e, 'message') and 'desc' in e.message:
                msg = e.message['desc']
            else:
                msg = e.args[0]['desc']
            self._log.debug('%s (%s)' % (msg, self._url))
            return False

        self._log.debug('LDAP connection established')
        return conn

    def _search(self, base, fltr, attrs=None, scope=ldap.SCOPE_SUBTREE):
        self._log.debug('Search base: %s, filter: %s, attributes: %s, scope: %s' % (base, fltr, attrs, scope))
        try:
            results = self._conn.search_s(base, scope, fltr, attrs)
        except (ldap.NO_SUCH_OBJECT, ldap.SERVER_DOWN) as e:
            self._log.debug(self._get_ldap_msg(e))
            results = False
        return results

    def _get_fqdn(self):
        self._log.debug('Grabbing FQDN from LDAP')
        results = self._search(
            'cn=config',
            '(objectClass=*)',
            ['nsslapd-localhost'],
            scope=ldap.SCOPE_BASE
        )

        if not results and type(results) is not list:
            r = None
        else:
            dn, attrs = results[0]
            r = attrs['nsslapd-localhost'][0].decode('utf-8')

        self._log.debug(r)
        return r

    def _get_context(self):
        self._log.debug('Grabbing default context from LDAP')
        results = self._search(
            'cn=config',
            '(objectClass=*)',
            ['nsslapd-defaultnamingcontext'],
            scope=ldap.SCOPE_BASE
        )

        if not results and type(results) is not list:
            r = None
        else:
            dn, attrs = results[0]
            r = attrs['nsslapd-defaultnamingcontext'][0].decode('utf-8')

        self._log.debug(r)
        return r

    def _count_users(self, user_base):
        self._log.debug('Counting %s users...' % user_base)
        results = self._search(
            getattr(self, '_%s_user_base' % user_base),
            '(objectClass=*)',
            ['numSubordinates'],
            scope=ldap.SCOPE_BASE
        )

        if not results and type(results) is not list:
            r = 0
        else:
            dn, attrs = results[0]
            r = attrs['numSubordinates'][0].decode('utf-8')

        self._log.debug(r)
        return r

    def _count_groups(self):
        self._log.debug('Counting groups...')
        results = self._search(
            self._groups_base,
            '(objectClass=ipausergroup)'
        )

        if not results and type(results) is not list:
            r = 0
        else:
            r = len(results)

        self._log.debug(r)
        return r

    def _count_hosts(self):
        self._log.debug('Counting hosts...')
        results = self._search(
            'cn=computers,cn=accounts,%s' % self._base_dn,
            '(fqdn=*)',
            ['dn']
        )

        if not results and type(results) is not list:
            r = 0
        else:
            r = len(results)

        self._log.debug(r)
        return r

    def _count_services(self):
        self._log.debug('Counting services...')
        results = self._search(
            'cn=services,cn=accounts,%s' % self._base_dn,
            '(krbprincipalname=*)',
            ['dn']
        )

        if not results and type(results) is not list:
            r = 0
        else:
            r = len(results)

        self._log.debug(r)
        return r

    def _count_netgroups(self):
        self._log.debug('Counting netgroups...')
        results = self._search(
            'cn=ng,cn=alt,%s' % self._base_dn,
            '(ipaUniqueID=*)',
            ['dn'],
            scope=ldap.SCOPE_ONELEVEL
        )

        if not results and type(results) is not list:
            r = 0
        else:
            r = len(results)

        self._log.debug(r)
        return r

    def _count_hostgroups(self):
        self._log.debug('Counting host groups...')
        results = self._search(
            'cn=hostgroups,cn=accounts,%s' % self._base_dn,
            '(objectClass=*)',
            ['numSubordinates'],
            scope=ldap.SCOPE_BASE
        )
        dn, attrs = results[0]
        r = attrs['numSubordinates'][0].decode('utf-8')
        self._log.debug(r)
        return r

    def _count_hbac_rules(self):
        self._log.debug('Counting HBAC rules...')
        results = self._search(
            'cn=hbac,%s' % self._base_dn,
            '(ipaUniqueID=*)',
            scope=ldap.SCOPE_ONELEVEL
        )
        r = len(results)
        self._log.debug(r)
        return r

    def _count_sudo_rules(self):
        self._log.debug('Counting SUDO rules...')
        results = self._search(
            'cn=sudorules,cn=sudo,%s' % self._base_dn,
            '(ipaUniqueID=*)',
            scope=ldap.SCOPE_ONELEVEL
        )
        r = len(results)
        self._log.debug(r)
        return r

    def _count_dns_zones(self):
        self._log.debug('Counting DNS zones...')
        results = self._search(
            'cn=dns,%s' % self._base_dn,
            '(|(objectClass=idnszone)(objectClass=idnsforwardzone))',
            scope=ldap.SCOPE_ONELEVEL
        )
        r = len(results)
        self._log.debug(r)
        return r

    def _count_certificates(self):
        self._log.debug('Counting certificates...')
        results = self._search(
            'ou=certificateRepository,ou=ca,o=ipaca',
            '(certStatus=*)',
            scope=ldap.SCOPE_ONELEVEL
        )

        if not results and type(results) is not list:
            r = 0
        else:
            r = len(results)

        self._log.debug(r)
        return r

    def _count_ldap_conflicts(self):
        self._log.debug('Checking for LDAP conflicts...')
        results = self._search(
            self._base_dn,
            '(nsds5ReplConflict=*)',
            ['nsds5ReplConflict']
        )

        if not results and type(results) is not list:
            r = 0
        else:
            r = len(results)

        self._log.debug(r)
        return r

    def _ghost_replicas(self):
        self._log.debug('Checking for ghost replicas...')
        results = self._search(
            self._base_dn,
            '(&(objectclass=nstombstone)(nsUniqueId=ffffffff-ffffffff-ffffffff-ffffffff))',
            ['nscpentrywsi']
        )

        r = 0

        if type(results) == list and len(results) > 0:
            dn, attrs = results[0]

            for attr in attrs['nscpentrywsi']:
                if 'replica ' in str(attr) and 'ldap' not in str(attr):
                    r += 1

        self._log.debug(r)
        return r

    def _anon_bind(self):
        self._log.debug('Checking for anonymous bind...')
        results = self._search(
            'cn=config',
            '(objectClass=*)',
            ['nsslapd-allow-anonymous-access'],
            scope=ldap.SCOPE_BASE
        )
        dn, attrs = results[0]
        state = attrs['nsslapd-allow-anonymous-access'][0].decode('utf-8')

        if state in ['on', 'off', 'rootdse']:
            r = str(state).upper()
        else:
            r = 'ERROR'

        self._log.debug(r)
        return r

    def _ms_adtrust(self):
        self._log.debug('Checking for MS ADTrust DNS records...')
        record = '_kerberos._tcp.Default-First-Site-Name._sites.dc._msdcs.%s' % self._domain

        r = False

        try:
            answers = dns.resolver.query(record, 'SRV')
        except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
            self._log.debug(r)
            return r

        for answer in answers:
            if self._fqdn in answer.to_text():
                r = True
                self._log.debug(r)
                return r

        self._log.debug(r)
        return r

    def _replication_agreements(self):
        self._log.debug('Checking for replication agreements...')
        msg = []
        healthy = True
        suffix = self._base_dn.replace('=', '\\3D').replace(',', '\\2C')
        results = self._search(
            'cn=replica,cn=%s,cn=mapping tree,cn=config' % suffix,
            '(objectClass=*)',
            ['nsDS5ReplicaHost', 'nsds5replicaLastUpdateStatus'],
            scope=ldap.SCOPE_ONELEVEL
        )

        for result in results:
            dn, attrs = result
            host = attrs['nsDS5ReplicaHost'][0].decode('utf-8')
            host = host.replace('.%s' % self._domain, '')
            status = attrs['nsds5replicaLastUpdateStatus'][0].decode('utf-8')
            status = status.replace('Error ', '').partition(' ')[0].strip('()')
            if status not in ['0']:
                healthy = False
            msg.append('%s %s' % (host, status))

        r1 = '\n'.join(msg)
        r2 = healthy
        self._log.debug('%s, %s' % (r1, r2))
        return r1, r2
