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
    def __init__(self, fqdn, binddn, bindpw):
        self._log = logging.getLogger()
        self._log.debug('Initialising FreeIPA server %s' % fqdn)
        self.fqdn = fqdn
        self.hostname_short = fqdn.partition('.')[0]
        self._domain = fqdn.partition('.')[2]
        self._binddn = binddn
        self._bindpw = bindpw
        self._url = 'ldaps://' + fqdn
        self._base_dn = 'dc=' + fqdn.partition('.')[2].replace('.', ',dc=')
        self._active_user_base = 'cn=users,cn=accounts,' + self._base_dn
        self._stage_user_base = 'cn=staged users,cn=accounts,cn=provisioning,' + self._base_dn
        self._preserved_user_base = 'cn=deleted users,cn=accounts,cn=provisioning,' + self._base_dn
        self._groups_base = 'cn=groups,cn=accounts,' + self._base_dn

        ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)

        try:
            self._conn = ldap.initialize(self._url)
            self._conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 3)
            self._conn.simple_bind_s(self._binddn, self._bindpw)
        except (
            ldap.SERVER_DOWN,
            ldap.NO_SUCH_OBJECT,
            ldap.INVALID_CREDENTIALS
        ) as e:
            if hasattr(e, 'message') and 'desc' in e.message:
                msg = e.message['desc']
            else:
                msg = e.args[0]['desc']
            self._log.critical('Bind error: %s (%s)' % (msg, self.fqdn))
            exit(1)

        self.users = self._count_users(user_base='active')
        self.ustage = self._count_users(user_base='stage')
        self.upres = self._count_users(user_base='preserved')
        self.ugroups = self._count_groups()
        self.hosts = self._count_hosts()
        self.hgroups = self._count_hostgroups()
        self.hbac = self._count_hbac_rules()
        self.sudo = self._count_sudo_rules()
        self.zones = self._count_dns_zones()
        self.certs = self._count_certificates()
        self.ldap = self._ldap_conflicts()
        self.ghosts = self._ghost_replicas()
        self.bind = self._anon_bind()
        self.msdcs = self._ms_adtrust()
        self.replica, self.healthy_agreements = self._replication_agreements()

    def _search(self, base, fltr, attrs=None, scope=ldap.SCOPE_SUBTREE):
        results = self._conn.search_s(base, scope, fltr, attrs)
        return results

    def _count_users(self, user_base):
        self._log.debug('Counting %s users...' % user_base)
        results = self._search(
            getattr(self, '_%s_user_base' % user_base),
            '(objectClass=*)',
            ['numSubordinates'],
            scope=ldap.SCOPE_BASE
        )
        dn, attrs = results[0]
        return attrs['numSubordinates'][0].decode('utf-8')

    def _count_groups(self):
        self._log.debug('Counting groups...')
        results = self._search(
            self._groups_base,
            '(objectClass=ipausergroup)'
        )
        return len(results)

    def _count_hosts(self):
        self._log.debug('Counting hosts...')
        results = self._search(
            'cn=computers,cn=accounts,%s' % self._base_dn,
            '(objectClass=*)',
            ['numSubordinates'],
            scope=ldap.SCOPE_BASE
        )
        dn, attrs = results[0]
        return attrs['numSubordinates'][0].decode('utf-8')

    def _count_hostgroups(self):
        self._log.debug('Counting host groups...')
        results = self._search(
            'cn=hostgroups,cn=accounts,%s' % self._base_dn,
            '(objectClass=*)',
            ['numSubordinates'],
            scope=ldap.SCOPE_BASE
        )
        dn, attrs = results[0]
        return attrs['numSubordinates'][0].decode('utf-8')

    def _count_hbac_rules(self):
        self._log.debug('Counting HBAC rules...')
        results = self._search(
            'cn=hbac,%s' % self._base_dn,
            '(ipaUniqueID=*)',
            scope=ldap.SCOPE_ONELEVEL
        )
        return len(results)

    def _count_sudo_rules(self):
        self._log.debug('Counting SUDO rules...')
        results = self._search(
            'cn=sudorules,cn=sudo,%s' % self._base_dn,
            '(ipaUniqueID=*)',
            scope=ldap.SCOPE_ONELEVEL
        )
        return len(results)

    def _count_dns_zones(self):
        self._log.debug('Counting DNS zones...')
        results = self._search(
            'cn=dns,%s' % self._base_dn,
            '(|(objectClass=idnszone)(objectClass=idnsforwardzone))',
            scope=ldap.SCOPE_ONELEVEL
        )
        return len(results)

    def _count_certificates(self):
        self._log.debug('Counting certificates...')
        try:
            results = self._search(
                'ou=certificateRepository,ou=ca,o=ipaca',
                '(certStatus=*)',
                scope=ldap.SCOPE_ONELEVEL
            )
        except ldap.NO_SUCH_OBJECT:
            return 'N/A'
        n = len(results)
        return n

    def _ldap_conflicts(self):
        self._log.debug('Checking for LDAP conflicts...')
        results = self._search(
            self._base_dn,
            '(nsds5ReplConflict=*)',
            ['nsds5ReplConflict']
        )
        n = len(results)
        return 'YES' if n > 0 else 'NO'

    def _ghost_replicas(self):
        self._log.debug('Checking for ghost replicas...')
        results = self._search(
            self._base_dn,
            '(&(objectclass=nstombstone)(nsUniqueId=ffffffff-ffffffff-ffffffff-ffffffff))',
            ['nscpentrywsi']
        )
        dn, attrs = results[0]
        n = 0
        for attr in attrs['nscpentrywsi']:
            if 'replica ' in str(attr) and 'ldap' not in str(attr):
                n += 1
        return 'YES' if n > 0 else 'NO'

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
        if state == 'on':
            return 'YES'
        elif state == 'off':
            return 'NO'
        elif state == 'rootdse':
            return 'ROOTDSE'
        else:
            return 'ERROR'

    def _ms_adtrust(self):
        record = '_kerberos._tcp.Default-First-Site-Name._sites.dc._msdcs.%s' % self._domain

        try:
            answers = dns.resolver.query(record, 'SRV')
        except (dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
            return 'NO'

        for answer in answers:
            if self.fqdn in answer.to_text():
                return 'YES'

        return 'NO'

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
            host = host.partition('.')[0]
            status = attrs['nsds5replicaLastUpdateStatus'][0].decode('utf-8')
            status = status.replace('Error ', '').partition(' ')[0].strip('()')
            if status != '0':
                healthy = False
            msg.append('%s %s' % (host, status))

        return '\n'.join(msg), healthy
