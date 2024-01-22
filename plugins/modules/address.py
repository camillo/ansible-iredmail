#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2024 Daniel Marohn
# GNU General Public License v3.0+ (see LICENSES/GPL-3.0-or-later.txt or https://www.gnu.org/licenses/gpl-3.0.txt)
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: address
short_description: Manage iRedMail alias and forwardings
description:
- Create Alias in vmail
- Create forwardings
options:
  src_address:
    description:
      - Source address, the forwarding or alias should be created for
    type: str
    required: true
  dest_address:
    description:
      - Destination address, the forwarding should be created for
    type: str
  state:
    description:
      - Whether to create or remove the alias and/or forwarding
      - if dest_address is not set, all forwardings and the alias are removed
      - if dest_address is set, only the forwarding is removed
    type: str
    choices: [ "alias", "forwarding", "absent" ]
    default: alias
  name:
    description:
      - Name of the alias
      - If not set, the name is extracted from the source address
    type: str
  expired:
    description:
      - Date, when the alias expires
    type: str
  active:
    description:
      - Whether the alias or forwarding is active
    type: bool
    default: true
  login_db:
    description:
      - The vmail database to use
    type: str
    default: 'vmail'
requirements:
  - community.mysql
attributes:
  check_mode:
    support: full
seealso:
  - module: community.mysql
author:
  - Daniel Marohn (@danielmarohn)
extends_documentation_fragment:
- camillo.iredmail.mysql
'''

EXAMPLES = r'''
- name: Create an alias foo@bar.baz without forwarding
  vmail:
    login_host: "{{ mysql.host }}"
    login_user: "{{ mysql.user }}"
    login_password: "{{ mysql.password }}"
    src_address: "foo@bar.baz"

- name: Create an alias foo@bar.baz forwarding to boo@bar.baz
  vmail:
    login_host: "{{ mysql.host }}"
    login_user: "{{ mysql.user }}"
    login_password: "{{ mysql.password }}"
    src_address: "foo@bar.baz"
    dest_address: "boo@bar.baz"

- name: Create a forwarding from foo@bar.baz to boo@bar.baz
  vmail:
    login_host: "{{ mysql.host }}"
    login_user: "{{ mysql.user }}"
    login_password: "{{ mysql.password }}"
    src_address: "foo@bar.baz"
    dest_address: "boo@bar.baz"
    state: "forwarding"

- name: Delete the forwarding from foo@bar.baz to boo@bar.baz; keep the alias if it exists
  vmail:
    login_host: "{{ mysql.host }}"
    login_user: "{{ mysql.user }}"
    login_password: "{{ mysql.password }}"
    src_address: "foo@bar.baz"
    dest_address: "boo@bar.baz"
    state: "absent"

- name: Delete the alias and all forwardings
  vmail:
    login_host: "{{ mysql.host }}"
    login_user: "{{ mysql.user }}"
    login_password: "{{ mysql.password }}"
    src_address: "foo@bar.baz"
    state: "absent"
'''

RETURN = r'''
alias:
  description: Alias row from database.
  returned: always
  type: dict
  sample:
    accesspolicy: ""
    active: 0
    address: "foo@bar.baz"
    created: "2024-01-21T02:07:52"
    domain: "bar.baz"
    expired: "9999-12-31T00:00:00"
    modified: "2024-01-21T02:07:52"
    name: "foo"
forwarding:
    description: Forwarding row from database.
    returned: always
    type: dict
    sample:
      active: 0
      address: "foo@bar.baz"
      dest_domain: "foobar.baz"
      domain: "bar.baz"
      forwarding: "boo@foobar.baz"
      id: 42
      is_alias: 1
      is_forwarding: 0
      is_list: 0
      is_maillist: 0
'''


import re
from ansible.module_utils._text import to_native
from ansible.module_utils.basic import missing_required_lib
import traceback

try:
    # from ansible_collections.community.mysql.plugins.module_utils.mysql import mysql_common_argument_spec
    from ansible_collections.community.mysql.plugins.module_utils.mysql import (
        mysql_connect,
        mysql_driver,
        mysql_driver_fail_msg,
    )
except ImportError:
    HAS_COMMUNITY_MYSQL = False
    COMMUNITY_MYSQL_ERROR = traceback.format_exc()
else:
    HAS_COMMUNITY_MYSQL = True
    COMMUNITY_MYSQL_ERROR = None

from ansible.module_utils.basic import AnsibleModule
__metaclass__ = type


def email(value):
    if value is None:
        return None
    match = re.match(
        r"\b([A-Z0-9._%+-]+)@([A-Z0-9.-]+\.[A-Z]{2,})\b", value, re.IGNORECASE | re.VERBOSE)
    if match is None:
        raise ValueError("Not a valid email address: %s" % value)

    return {
        "address": match.group(0),
        "name": match.group(1),
        "domain": match.group(2)
    }


def mysql_common_argument_spec():
    return dict(
        login_user=dict(type='str', default=None),
        login_password=dict(type='str', no_log=True),
        login_host=dict(type='str', default='localhost'),
        login_port=dict(type='int', default=3306),
        login_unix_socket=dict(type='str'),
        config_file=dict(type='path', default='~/.my.cnf'),
        connect_timeout=dict(type='int', default=30),
        client_cert=dict(type='path', aliases=['ssl_cert']),
        client_key=dict(type='path', aliases=['ssl_key']),
        ca_cert=dict(type='path', aliases=['ssl_ca']),
        check_hostname=dict(type='bool', default=None),
    )


def vmail_argument_spec():
    argument_spec = mysql_common_argument_spec()
    argument_spec.update(
        src_address=dict(type='str', required=True),
        dest_address=dict(type='str'),
        login_db=dict(type='str', default='vmail'),
        name=dict(type='str'),
        state=dict(type='str', choices=["alias", "forwarding", "absent"], default="alias"),
        active=dict(type='bool', default=True),
        expired=dict(type='str'),
    )

    return argument_spec


def create_ansible_module():
    argument_spec = vmail_argument_spec()

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True
    )

    module.params["src_address"] = email(module.params["src_address"])
    module.params["dest_address"] = email(module.params["dest_address"])

    if not HAS_COMMUNITY_MYSQL:
        module.fail_json(
            msg=missing_required_lib('community.mysql', COMMUNITY_MYSQL_ERROR)
        )

    return module


def db_connect(module):
    if mysql_driver is None:
        module.fail_json(msg=mysql_driver_fail_msg)

    try:
        config_file = module.params['config_file']
        return mysql_connect(
            module=module,
            login_user=module.params['login_user'],
            login_password=module.params['login_password'],
            config_file=config_file,
            ssl_cert=module.params['client_cert'],
            ssl_key=module.params['client_key'],
            ssl_ca=module.params['ca_cert'],
            db=module.params['login_db'],
            check_hostname=module.params['check_hostname'],
            connect_timeout=module.params['connect_timeout'],
            cursor_class='DictCursor', autocommit=False)
    except Exception as e:
        module.fail_json(msg="unable to connect to database, check login_user and "
                             "login_password are correct or %s has the credentials. "
                             "Exception message: %s" % (config_file, to_native(e)))


def delete(module, cursor):
    src_address = module.params["src_address"]
    dest_address = module.params["dest_address"]
    if dest_address is None:
        cursor.execute("DELETE FROM alias WHERE address=%s",
                       src_address["address"])
        changed = cursor.rowcount > 0
        cursor.execute("DELETE FROM forwardings WHERE address=%s",
                       src_address["address"])
        return changed or cursor.rowcount > 0
    cursor.execute("DELETE FROM forwardings WHERE address=%s AND forwarding=%s",
                   (src_address["address"], dest_address["address"]))
    return cursor.rowcount > 0


def fetch_alias(module, cursor):
    address = module.params["src_address"]["address"]
    cursor.execute("SELECT * FROM alias WHERE address=%s", address)
    return cursor.rowcount > 0


def create_alias(module, cursor):
    src_address = module.params["src_address"]
    domain = src_address["domain"]
    name = module.params['name']
    name = name if name is not None else src_address["name"]
    expired = module.params['expired']
    expired = expired if expired is not None else "9999-12-31"
    active = module.params['active']
    cursor.execute("INSERT INTO alias (address, name, domain, created, modified, expired, active) VALUES (%s, %s, %s, now(), now(), %s, %s)",
                   (src_address["address"], name, domain, expired, active))
    fetch_alias(module, cursor)
    return cursor.fetchone()


def update_alias(module, db_alias, cursor):
    name = module.params['name']
    expired = module.params['expired']
    active = module.params['active']
    address = module.params["src_address"]["address"]
    if (name is not None and db_alias["name"] != name) \
            or (expired is not None and str(db_alias["expired"]) != expired) \
            or (active is not None and db_alias["active"] != active):
        name = name if name is not None else db_alias["name"]
        expired = expired if expired is not None else db_alias["expired"]
        cursor.execute("UPDATE alias SET name=%s, modified=now(), expired=%s, active=%s WHERE address=%s",
                       (name, expired, active, address))
        fetch_alias(module, cursor)
        return True, cursor.fetchone()
    return False, db_alias


def create_or_update_alias(module, cursor, db_connection):
    try:
        if fetch_alias(module, cursor):
            return update_alias(module, cursor.fetchone(), cursor)
        else:
            return True, create_alias(module, cursor)
    except Exception as e:
        db_connection.rollback()
        module.fail_json(
            msg="unable to update or create alias: %s" % to_native(e))


def create_forwarding(module, cursor, db_connection):
    # state, src_address, dest_address, active
    state = module.params['state']
    src_address = module.params["src_address"]
    dest_address = module.params["dest_address"]
    active = module.params['active']

    def fetch_forwarding(db_cursor):
        return db_cursor.execute(
            "SELECT * FROM forwardings WHERE address=%s AND forwarding=%s", (src_address["address"], dest_address["address"]))
    try:
        fetch_forwarding(cursor)
        is_alias = state == "alias"
        if cursor.rowcount == 0:
            cursor.execute("""
                           INSERT INTO forwardings (address, forwarding, domain, dest_domain, is_alias, is_forwarding, active)
                           VALUES (%s, %s, %s, %s, %s, %s, %s)
                           """,
                           (src_address["address"], dest_address["address"], src_address["domain"], dest_address["domain"], is_alias, not is_alias, active))
            fetch_forwarding(cursor)
            return True, cursor.fetchone()
        else:
            db_forwarding = cursor.fetchone()
            if db_forwarding["active"] != active \
                    or db_forwarding["domain"] != src_address["domain"] \
                    or db_forwarding["dest_domain"] != dest_address["domain"] \
                    or db_forwarding["is_alias"] != is_alias \
                    or db_forwarding["is_forwarding"] == is_alias:
                cursor.execute("UPDATE forwardings SET domain=%s, dest_domain=%s, active=%s, is_alias=%s, is_forwarding=%s WHERE address=%s AND forwarding=%s",
                               (src_address["domain"], dest_address["domain"], active, is_alias, not is_alias, src_address["address"], dest_address["address"]))
                fetch_forwarding(cursor)
                return True, cursor.fetchone()
    except Exception as e:
        db_connection.rollback()
        module.fail_json(
            msg="unable to update or create forwarding: %s" % to_native(e))
    return False, db_forwarding


def finalize_transaction(module, db_connection):
    if module.check_mode:
        module.log("check_mode: rollback transaction")
        db_connection.rollback()
    else:
        db_connection.commit()


def main():
    module = create_ansible_module()
    cursor, db_connection = db_connect(module)

    changed = False
    db_alias = {}
    db_forwarding = {}

    if module.params['state'] == "absent":
        changed = delete(module, cursor)
    else:
        if module.params['state'] == "alias":
            changed, db_alias = create_or_update_alias(
                module, cursor, db_connection)

        if module.params["dest_address"] is not None:
            changed_forwarding, db_forwarding = create_forwarding(
                module, cursor, db_connection)
            changed = changed or changed_forwarding

    finalize_transaction(module, db_connection)

    module.exit_json(
        changed=changed,
        alias=db_alias,
        forwarding=db_forwarding)


if __name__ == '__main__':
    main()
