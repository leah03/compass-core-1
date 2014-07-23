# Copyright 2014 Huawei Technologies Co. Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Host database operations."""
import logging

from compass.db.api import database
from compass.db.api import metadata_holder as metadata_api
from compass.db.api import permission
from compass.db.api import user as user_api
from compass.db.api import utils
from compass.db import exception
from compass.db import models


SUPPORTED_FIELDS = ['name', 'os_name', 'owner', 'mac']
SUPPORTED_NETOWORK_FIELDS = [
    'interface', 'ip', 'subnet', 'is_mgmt', 'is_promiscuous'
]
RESP_FIELDS = [
    'id', 'name', 'os_name', 'owner', 'mac',
    'reinstall_os', 'os_installed', 'tag', 'location',
    'created_at', 'updated_at'
]
RESP_CLUSTER_FIELDS = [
    'id', 'name', 'os_name', 'reinstall_distributed_system',
    'distributed_system_name', 'owner', 'adapter_id',
    'distributed_system_installed',
    'adapter_id', 'created_at', 'updated_at'
]
RESP_NETWORK_FIELDS = [
    'id', 'ip', 'interface', 'netmask', 'is_mgmt', 'is_promiscuous'
]
RESP_CONFIG_FIELDS = [
    'os_config',
]
UPDATED_FIELDS = ['name', 'reinstall_os']
UPDATED_CONFIG_FIELDS = [
    'put_os_config'
]
PATCHED_CONFIG_FIELDS = [
    'patched_os_config'
]
ADDED_NETWORK_FIELDS = [
    'interface', 'ip', 'subnet_id'
]
OPTIONAL_ADDED_NETWORK_FIELDS = ['is_mgmt', 'is_promiscuous']
UPDATED_NETWORK_FIELDS = [
    'interface', 'ip', 'subnet_id', 'subnet', 'is_mgmt',
    'is_promiscuous'
]
RESP_STATE_FIELDS = [
    'id', 'state', 'progress', 'message'
]
UPDATED_STATE_FIELDS = [
    'id', 'state', 'progress', 'message'
]


@utils.supported_filters(optional_support_keys=SUPPORTED_FIELDS)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_HOSTS
)
@utils.wrap_to_dict(RESP_FIELDS)
def list_hosts(session, lister, **filters):
    """List hosts."""
    return utils.list_db_objects(
        session, models.Host, **filters
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_HOSTS
)
@utils.wrap_to_dict(RESP_FIELDS)
def get_host(session, getter, host_id, **kwargs):
    """get host info."""
    return utils.get_db_object(
        session, models.Host, id=host_id
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_HOST_CLUSTERS
)
@utils.wrap_to_dict(RESP_CLUSTER_FIELDS)
def get_host_clusters(session, getter, host_id, **kwargs):
    """get host clusters."""
    host = utils.get_db_object(
        session, models.Host, id=host_id
    )
    return [clusterhost.cluster for clusterhost in host.clusterhosts]


def _conditional_exception(host, exception_when_not_editable):
    if exception_when_not_editable:
        raise exception.Forbidden(
            'host %s is not editable' % host.name
        )
    else:
        return False


def is_host_editable(
    session, host, user,
    reinstall_os_set=False, exception_when_not_editable=True
):
    with session.begin(subtransactions=True):
        if reinstall_os_set:
            if host.state.state == 'INSTALLING':
                return _conditional_exception(
                    host, exception_when_not_editable
                )
        elif not host.reinstall_os:
            return _conditional_exception(
                host, exception_when_not_editable
            )
        if not user.is_admin and host.creator_id != user.id:
            return _conditional_exception(
                host, exception_when_not_editable
            )
    return True


@utils.supported_filters(UPDATED_FIELDS)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_UPDATE_HOST
)
@utils.wrap_to_dict(RESP_FIELDS)
def update_host(session, updater, host_id, **kwargs):
    """Update a host."""
    host = utils.get_db_object(
        session, models.Host, id=host_id
    )
    is_host_editable(
        session, host, updater,
        reinstall_os_set=kwargs.get('reinstall_os', False)
    )
    return utils.update_db_object(session, host, **kwargs)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_HOST
)
@utils.wrap_to_dict(RESP_FIELDS)
def del_host(session, deleter, host_id, **kwargs):
    """Delete a host."""
    host = utils.get_db_object(
        session, models.Host, id=host_id
    )
    is_host_editable(session, host, deleter)
    return utils.del_db_object(session, host)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_HOST_CONFIG
)
@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def get_host_config(session, getter, host_id, **kwargs):
    """Get host config."""
    return utils.get_db_object(
        session, models.Host, id=host_id
    )


@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_HOST_CONFIG
)
@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def _update_host_config(session, updater, host_id, **kwargs):
    """Update host config."""
    host = utils.get_db_object(
        session, models.Host, id=host_id
    )
    is_host_editable(session, host, updater)
    utils.update_db_object(session, host, config_validated=False, **kwargs)
    os_config = host.os_config
    if os_config:
        metadata_api.validate_os_config(
            os_config, host.adapter_id
        )
    return host


@utils.supported_filters(UPDATED_CONFIG_FIELDS)
@database.run_in_session()
def update_host_config(session, updater, host_id, **kwargs):
    return _update_host_config(session, updater, host_id, **kwargs)


@utils.supported_filters(PATCHED_CONFIG_FIELDS)
@database.run_in_session()
def patch_host_config(session, updater, host_id, **kwargs):
    return _update_host_config(session, updater, host_id, **kwargs)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_HOST_CONFIG
)
@utils.wrap_to_dict(RESP_CONFIG_FIELDS)
def del_host_config(session, deleter, host_id):
    """delete a host config."""
    host = utils.get_db_object(
        session, models.Host, id=host_id
    )
    is_host_editable(session, host, deleter)
    return utils.update_db_object(
        session, host, os_config={}, config_validated=False
    )


@utils.supported_filters(
    optional_support_keys=SUPPORTED_NETOWORK_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_HOST_NETWORKS
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def list_host_networks(session, lister, host_id, **filters):
    """Get host networks."""
    return utils.list_db_objects(
        session, models.HostNetwork,
        host_id=host_id, **filters
    )


@utils.supported_filters(
    optional_support_keys=SUPPORTED_NETOWORK_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_HOST_NETWORKS
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def list_hostnetworks(session, lister, **filters):
    """Get host networks."""
    return utils.list_db_objects(
        session, models.HostNetwork, **filters
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_HOST_NETWORKS
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def get_host_network(session, getter, host_id, subnet_id, **kwargs):
    """Get host network."""
    return utils.get_db_object(
        session, models.HostNetwork,
        host_id=host_id, subnet_id=subnet_id
    )


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_LIST_HOST_NETWORKS
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def get_hostnetwork(session, getter, host_network_id, **kwargs):
    """Get host network."""
    return utils.get_db_object(
        session, models.HostNetwork,
        id=host_network_id
    )


@utils.supported_filters(
    ADDED_NETWORK_FIELDS, optional_support_keys=OPTIONAL_ADDED_NETWORK_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_HOST_NETWORK
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def add_host_network(session, creator, host_id, **kwargs):
    """Create a host network."""
    host = utils.get_db_object(
        session, models.Host, id=host_id
    )
    is_host_editable(session, host, creator)
    return utils.add_db_object(
        session, models.HostNetwork, True,
        host_id, **kwargs
    )


@utils.supported_filters(
    optional_support_keys=UPDATED_NETWORK_FIELDS
)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_HOST_NETWORK
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def update_host_network(session, updater, host_id, subnet_id, **kwargs):
    """Update a host network."""
    host_network = utils.get_db_object(
        session, models.HostNetwork,
        host_id=host_id, subnet_id=subnet_id
    )
    is_host_editable(session, host_network.host, updater)
    return utils.update_db_object(session, host_network, **kwargs)


@utils.supported_filters(UPDATED_NETWORK_FIELDS)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_ADD_HOST_NETWORK
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def update_hostnetwork(session, updater, host_network_id, **kwargs):
    """Update a host network."""
    host_network = utils.get_db_object(
        session, models.HostNetwork, id=host_network_id
    )
    is_host_editable(session, host_network.host, updater)
    return utils.update_db_object(session, host_network, **kwargs)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_HOST_NETWORK
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def del_host_network(session, deleter, host_id, subnet_id, **kwargs):
    """Delete a host network."""
    host_network = utils.get_db_object(
        session, models.HostNetwork,
        host_id=host_id, subnet_id=subnet_id
    )
    is_host_editable(session, host_network.host, deleter)
    return utils.del_db_object(session, host_network)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_DEL_HOST_NETWORK
)
@utils.wrap_to_dict(RESP_NETWORK_FIELDS)
def del_hostnetwork(session, deleter, host_network_id, **kwargs):
    """Delete a host network."""
    host_network = utils.get_db_object(
        session, models.HostNetwork, id=host_network_id
    )
    is_host_editable(session, host_network.host, deleter)
    return utils.del_db_object(session, host_network)


@utils.supported_filters([])
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_GET_HOST_STATE
)
@utils.wrap_to_dict(RESP_STATE_FIELDS)
def get_host_state(session, getter, host_id, **kwargs):
    """Get host state info."""
    return utils.get_db_object(
        session, models.Host, id=host_id
    ).state_dict()


@utils.supported_filters(UPDATED_STATE_FIELDS)
@database.run_in_session()
@user_api.check_user_permission_in_session(
    permission.PERMISSION_UPDATE_HOST_STATE
)
@utils.wrap_to_dict(RESP_STATE_FIELDS)
def update_host_state(session, updater, host_id, **kwargs):
    """Update a host state."""
    host = utils.get_db_object(
        session, models.Host, id=host_id
    )
    utils.update_db_object(session, host.state, **kwargs)
    return host.state_dict()