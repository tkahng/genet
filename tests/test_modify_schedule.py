import pytest
from genet.modify import schedule
from genet.utils import spatial
from genet.core import Network, Schedule
from genet.schedule_elements import Service, Route, Stop
from tests.fixtures import assert_semantically_equal


@pytest.fixture()
def network():
    n = Network('epsg:27700')
    n.add_node('node_1', x_y=(1, 2))
    n.add_node('node_2', x_y=(1, 3))
    n.add_node('node_3', x_y=(2, 3))
    n.add_node('node_4', x_y=(2, 2))
    n.add_node('node_5', x_y=(3, 2))
    n.add_node('node_6', x_y=(4, 2))
    n.add_node('node_7', x_y=(5, 2))
    n.add_node('node_8', x_y=(6, 2))
    n.add_node('node_9', x_y=(6, 2))

    n.add_link('link_1', 'node_1', 'node_2', attribs={'length': 1, 'modes': ['car']})
    n.add_link('link_2', 'node_1', 'node_2', attribs={'length': 1, 'modes': ['bus']})
    n.add_link('link_3', 'node_2', 'node_3', attribs={'length': 1, 'modes': ['car']})
    n.add_link('link_4', 'node_3', 'node_4', attribs={'length': 1, 'modes': ['car']})
    n.add_link('link_5', 'node_1', 'node_4', attribs={'length': 1, 'modes': ['bus']})
    n.add_link('link_6', 'node_4', 'node_5', attribs={'length': 1, 'modes': ['car']})
    n.add_link('link_7', 'node_5', 'node_6', attribs={'length': 1, 'modes': ['car']})
    n.add_link('link_8', 'node_6', 'node_7', attribs={'length': 1, 'modes': ['car']})
    n.add_link('link_9', 'node_7', 'node_8', attribs={'length': 1, 'modes': ['car']})
    n.add_link('link_10', 'node_8', 'node_9', attribs={'length': 1, 'modes': ['car']})

    n.schedule = Schedule(epsg='epsg:27700',
                          services=[
                              Service(id='service_1',
                                      routes=[
                                          Route(id='service_1_route_1',
                                                route_short_name='',
                                                mode='bus',
                                                stops=[Stop(epsg='epsg:27700', id='stop_1', x=1, y=2.5),
                                                       Stop(epsg='epsg:27700', id='stop_2', x=2, y=2.5)],
                                                trips={'trip_1': '15:30:00'},
                                                arrival_offsets=['00:00:00', '00:02:00'],
                                                departure_offsets=['00:00:00', '00:03:00']
                                                ),
                                          Route(id='service_1_route_2',
                                                route_short_name='',
                                                mode='bus',
                                                stops=[Stop(epsg='epsg:27700', id='stop_2', x=2, y=2.5),
                                                       Stop(epsg='epsg:27700', id='stop_3', x=5.5, y=2)],
                                                trips={'trip_1': '16:30:00'},
                                                arrival_offsets=['00:00:00', '00:02:00'],
                                                departure_offsets=['00:00:00', '00:03:00']
                                                )
                          ]),
                              Service(id='service_rail',
                                      routes=[
                                          Route(id='service_rail_route_2',
                                                route_short_name='',
                                                mode='rail',
                                                stops=[Stop(epsg='epsg:27700', id='stop_1', x=1, y=2.5),
                                                       Stop(epsg='epsg:27700', id='stop_2', x=2, y=2.5)],
                                                trips={'trip_1': '15:30:00'},
                                                arrival_offsets=['00:00:00', '00:02:00'],
                                                departure_offsets=['00:00:00', '00:03:00']
                                                ),
                                          Route(id='service_rail_route_2',
                                                route_short_name='',
                                                mode='rail',
                                                stops=[Stop(epsg='epsg:27700', id='stop_2', x=2, y=2.5),
                                                       Stop(epsg='epsg:27700', id='stop_3', x=5.5, y=2)],
                                                trips={'trip_1': '16:30:00'},
                                                arrival_offsets=['00:00:00', '00:02:00'],
                                                departure_offsets=['00:00:00', '00:03:00']
                                                )
                          ])])
    return n


def assert_correct_routing_for_service_1(network):
    n = 0
    assert network.schedule['service_1'].routes[n].stops[0].has_linkRefId
    assert network.schedule['service_1'].routes[n].stops[0].linkRefId == 'link_5'
    assert network.schedule['service_1'].routes[n].stops[1].has_linkRefId
    assert network.schedule['service_1'].routes[n].route
    if network.schedule['service_1'].routes[n].stops[1].linkRefId == 'link_6':
        assert network.schedule['service_1'].routes[n].route == ['link_5', 'link_6']
    elif network.schedule['service_1'].routes[n].stops[1].linkRefId == 'link_7':
        assert network.schedule['service_1'].routes[n].route == ['link_5', 'link_6', 'link_7']
    else:
        raise AssertionError

    n = 1
    assert network.schedule['service_1'].routes[n].stops[1].has_linkRefId
    assert network.schedule['service_1'].routes[n].stops[1].linkRefId == 'link_8'
    assert network.schedule['service_1'].routes[n].stops[0].has_linkRefId
    assert network.schedule['service_1'].routes[n].route
    if network.schedule['service_1'].routes[n].stops[0].linkRefId == 'link_6':
        assert network.schedule['service_1'].routes[n].route == ['link_6', 'link_7', 'link_8']
    elif network.schedule['service_1'].routes[n].stops[0].linkRefId == 'link_7':
        assert network.schedule['service_1'].routes[n].route == ['link_7', 'link_8']
    else:
        raise AssertionError


def test_find_routes_for_schedule(mocker, network):
    mocker.patch.object(spatial, 'find_closest_nodes',
                        side_effect=[['node_5', 'node_6'], ['node_7', 'node_8'], ['node_1', 'node_2']])
    schedule.find_routes_for_schedule(network, 30)
    assert_correct_routing_for_service_1(network)


def test_find_routes_for_service(mocker, network):
    mocker.patch.object(spatial, 'find_closest_nodes',
                        side_effect=[['node_5', 'node_6'], ['node_7', 'node_8'], ['node_1', 'node_2']])
    schedule.find_routes_for_service(network.graph, network.schedule['service_1'], 30)
    assert_correct_routing_for_service_1(network)


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
