checkipaconsistency aka cipa
============================

Formerly known as ipa_check_consistency and check_ipa_consistency

Tool to check consistency across FreeIPA servers
------------------------------------------------

The tool can be used as a standalone consistency checker as well as a
Nagios/Opsview plug-in (check `Nagios section
below <#nagios-plug-in-mode>`__ for more info).

The script was originally written and then developed in BASH (until
version
`v1.3.0 <https://github.com/peterpakos/checkipaconsistency/tree/v1.3.0>`__)
and eventually ported to Python in v2.0.0.

It has been tested with multiple FreeIPA 4.2+ deployments across a range
of operating systems.

Requirements:

-  FreeIPA 4.2+
-  Python 2.7+/3.3+
-  Python modules listed in
   `requirements.txt <https://github.com/peterpakos/checkipaconsistency/blob/master/requirements.txt>`__

If you spot any problems or have any improvement ideas then feel free to
open an issue and I will be glad to look into it for you.

Installation
------------

A recommended way of installing the tool is pip install.

Once installed, a command line tool ``cipa`` should be available in your
system's PATH.

pip install
~~~~~~~~~~~

The tool is available in PyPI and can be installed using pip:

::

    $ pip install --upgrade pip setuptools wheel
    $ pip install checkipaconsistency
    $ cipa --help

Please note, in RHEL/CentOS you may also need to install the following
packages:

::

    $ yum install python-devel openldap-devel

Manual install
~~~~~~~~~~~~~~

Run the following command to install required Python modules:

::

    $ git clone https://github.com/peterpakos/checkipaconsistency.git
    $ cd checkipaconsistency
    $ pip install -r requirements.txt
    $ ./cipa --help

Configuration
-------------

By default, the tool reads its configuration from
``~/.config/checkipaconsistency`` file (the location can be overridden
by setting environment variable ``XDG_CONFIG_HOME``). If the config file
(or directory) does not exist then it will be automatically created and
populated with sample config upon the next run. Alternatively, you can
specify all required options directly from the command line.

Help
----

::

    $ cipa --help
    usage: cipa [-H [HOSTS [HOSTS ...]]] [-d [DOMAIN]] [-D [BINDDN]] [-W [BINDPW]]
                [--help] [--version] [--debug] [--quiet] [-l [LOG_FILE]]
                [--no-header] [--no-border]
                [-n [{,all,users,susers,pusers,hosts,services,ugroups,hgroups,ngroups,hbac,sudo,zones,certs,conflicts,ghosts,bind,msdcs,replicas}]]
                [-w WARNING] [-c CRITICAL]

    Tool to check consistency across FreeIPA servers

    optional arguments:
      -H [HOSTS [HOSTS ...]], --hosts [HOSTS [HOSTS ...]]
                            list of IPA servers
      -d [DOMAIN], --domain [DOMAIN]
                            IPA domain
      -D [BINDDN], --binddn [BINDDN]
                            Bind DN (default: cn=Directory Manager)
      -W [BINDPW], --bindpw [BINDPW]
                            Bind password
      --help                show this help message and exit
      --version             show program's version number and exit
      --debug               debugging mode
      --quiet               do not log to console
      -l [LOG_FILE], --log-file [LOG_FILE]
                            log to file (./cipa.log by default)
      --no-header           disable table header
      --no-border           disable table border
      -n [{,all,users,susers,pusers,hosts,services,ugroups,hgroups,ngroups,hbac,sudo,zones,certs,conflicts,ghosts,bind,msdcs,replicas}]
                            Nagios plugin mode
      -w WARNING, --warning WARNING
                            number of failed checks before warning (default: 1)
      -c CRITICAL, --critical CRITICAL
                            number of failed checks before critical (default: 2)

Example
-------

::

    $ cipa -d ipa.example.com -W ********
    +--------------------+----------+----------+----------+-----------+----------+----------+-------+
    | FreeIPA servers:   | ipa01    | ipa02    | ipa03    | ipa04     | ipa05    | ipa06    | STATE |
    +--------------------+----------+----------+----------+-----------+----------+----------+-------+
    | Active Users       | 1199     | 1199     | 1199     | 1199      | 1199     | 1199     | OK    |
    | Stage Users        | 0        | 0        | 0        | 0         | 0        | 0        | OK    |
    | Preserved Users    | 0        | 0        | 0        | 0         | 0        | 0        | OK    |
    | Hosts              | 357      | 357      | 357      | 357       | 357      | 357      | OK    |
    | Services           | 49       | 49       | 49       | 49        | 49       | 49       | OK    |
    | User Groups        | 55       | 55       | 55       | 55        | 55       | 55       | OK    |
    | Host Groups        | 29       | 29       | 29       | 29        | 29       | 29       | OK    |
    | Netgroups          | 11       | 11       | 11       | 11        | 11       | 11       | OK    |
    | HBAC Rules         | 3        | 3        | 3        | 3         | 3        | 3        | OK    |
    | SUDO Rules         | 2        | 2        | 2        | 2         | 2        | 2        | OK    |
    | DNS Zones          | 114      | 114      | 114      | 114       | 114      | 114      | OK    |
    | Certificates       | 0        | 0        | 0        | 0         | 0        | 0        | OK    |
    | LDAP Conflicts     | 0        | 0        | 0        | 0         | 0        | 0        | OK    |
    | Ghost Replicas     | 0        | 0        | 0        | 0         | 0        | 0        | OK    |
    | Anonymous BIND     | ON       | ON       | ON       | ON        | ON       | ON       | OK    |
    | Microsoft ADTrust  | False    | False    | False    | False     | False    | False    | OK    |
    | Replication Status | ipa03 0  | ipa03 0  | ipa04 0  | ipa03 0   | ipa03 0  | ipa04 0  | OK    |
    |                    | ipa04 0  | ipa04 0  | ipa05 0  | ipa01 0   | ipa01 0  |          |       |
    |                    | ipa05 0  | ipa05 0  | ipa01 0  | ipa02 0   | ipa02 0  |          |       |
    |                    | ipa02 0  | ipa01 0  | ipa02 0  | ipa06 0   |          |          |       |
    +--------------------+----------+----------+----------+-----------+----------+----------+-------+

Debug mode
----------

If you experience any problems with the tool, try running it in the
debug mode:

::

    $ cipa --debug
    2017-12-22 20:05:04,494 [main] DEBUG Namespace(binddn=None, bindpw=None, critical=2, debug=True, disable_border=False, disable_header=False, domain=None, hosts=None, log_file=None, nagios_check=None, quiet=False, warning=1)
    2017-12-22 20:05:04,494 [main] DEBUG Initialising...
    2017-12-22 20:05:04,494 [main] DEBUG Config file not found at /Users/peter/.config/checkipaconsistency
    2017-12-22 20:05:04,494 [main] INFO Initial config saved to /Users/peter/.config/checkipaconsistency - PLEASE EDIT IT!
    2017-12-22 20:05:04,495 [main] CRITICAL IPA domain not set

Nagios plug-in mode
-------------------

The tool can be easily transformed into a Nagios/Opsview check:

::

    $ pip install checkipaconsistency
    $ su - nagios
    $ vim ~/.config/checkipaconsistency
    $ ln -s `which cipa` /usr/local/nagios/libexec/check_ipa_consistency

Perform all checks using default warning/critical thresholds:

::

    $ /usr/local/nagios/libexec/check_ipa_consistency -n all
    OK - 15/15 checks passed

Perform specific check with custom alerting thresholds:

::

    $ /usr/local/nagios/libexec/check_ipa_consistency -n users -w 2 -c3
    OK - Active Users

LDAP Conflicts
~~~~~~~~~~~~~~

Normally conflicting changes between replicas are resolved automatically
(the most recent change takes precedence). However, there are cases
where manual intervention is required. If you see LDAP conflicts in the
output of this script, you need to find the conflicting entries and
decide which of them should be preserved/deleted.

More information on solving common replication conflicts can be found
`here <https://access.redhat.com/documentation/en-us/red_hat_directory_server/10/html/administration_guide/managing_replication-solving_common_replication_conflicts>`__.
