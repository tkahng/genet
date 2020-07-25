from genet.modify import schedule
from genet.utils import spatial
from tests.fixtures import assert_semantically_equal
from tests.test_util_routing import network


def test_find_route_for_route(mocker, network):
    mocker.patch.object(spatial, 'find_closest_nodes',
                        side_effect=[['node_1', 'node_2'], ['node_5', 'node_6']])
    schedule.find_route_for_route(network.graph, network.schedule['service_1'].routes[0], 30)

    assert network.schedule['service_1'].routes[0].route
    assert network.schedule['service_1'].routes[0].route == ['link_5', 'link_6']
    assert network.schedule['service_1'].routes[0].stops[0].has_linkRefId
    assert network.schedule['service_1'].routes[0].stops[0].linkRefId == 'link_5'
    assert network.schedule['service_1'].routes[0].stops[1].has_linkRefId
    assert network.schedule['service_1'].routes[0].stops[1].linkRefId == 'link_6'
