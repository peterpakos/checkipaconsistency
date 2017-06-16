# ipa_check_consistency
The tool checks consistency across FreeIPA servers.

It can also be used as a Nagios/Opsview plug-in (check -n, -w and -c  options).

The tool has been tested in FreeIPA 4.2/4.3/4.4 (Centos 7.2/7.3, Fedora 24) environments.

Requirements:
* FreeIPA 4.2 or higher
* Bash 4.0 or higher

Any comments and improvement ideas are welcome.

## Usage
```
$ ./ipa_check_consistency -h
Usage: ipa_check_consistency [OPTIONS]
AVAILABLE OPTIONS:
-H  List of IPA servers (e.g.: "server1 server2.domain server3")
    Both short names and FQDNs are supported (FQDN if not within IPA domain)
-d  IPA domain (e.g.: "ipa.domain.com")
-s  LDAP root suffix, if not domain based (default: "dc=ipa,dc=domain,dc=com")
-D  BIND DN (default: cn=Directory Manager)
-W  BIND password (prompt for one if not supplied)
-p  Password file (default: ipa_check_consistency.passwd)
-n  Nagios plugin mode
    all     - all checks (-w and -c only relevant if -na used), default if incorrect value is passed
    users   - Active Users
    ustage  - Stage Users
    upres   - Preserved Users
    ugroups - User Groups
    hosts   - Hosts
    hgroups - Host Groups
    hbac    - HBAC Rules
    sudo    - SUDO Rules
    zones   - DNS Zones
    certs   - Certificates
    ldap    - LDAP Conflicts
    ghosts  - Ghost Replicas
    bind    - Anonymous BIND
-w  Warning threshold (0-12), number of failed checks before alerting (default: 1)
-c  Critical threshold (0-12), number of failed checks before alerting (default: 2)
-h  Print this help summary page
-v  Print version number
```

## Example
```
$ ./ipa_check_consistency -d ipa.domain.com -W '********'
FreeIPA servers:    ipa01    ipa02    STATE
===========================================
Active Users        4        4        OK
Stage Users         0        0        OK
Preserved Users     0        0        OK
User Groups         5        5        OK
Hosts               10       10       OK
Host Groups         1        1        OK
HBAC Rules          1        1        OK
SUDO Rules          1        1        OK
DNS Zones           11       11       OK
Certificates        N/A      N/A      OK
LDAP Conflicts      NO       NO       OK
Ghost Replicas      NO       NO       OK
Anonymous BIND      YES      YES      OK
Replication Status  ipa02 0  ipa01 0
===========================================
```

## Nagios/Opsview plug-in mode
```
$ ./ipa_check_consistency -H "ipa01 ipa02" -d ipa.domain.com -W '********' -n all
OK - 13/13 checks passed
$ echo $?
0
```
```
$ ./ipa_check_consistency -H "ipa01 ipa02" -d ipa.domain.com -W '********' -n users
OK - Active Users consistency
$ echo $?
0
```
