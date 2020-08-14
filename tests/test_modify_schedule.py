import pytest
from genet.modify import schedule as mod_schedule
from genet.utils import spatial
from genet.core import Network
from genet.schedule_elements import Schedule, Service, Route, Stop
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

    n.add_link('link_1', 'node_1', 'node_2', attribs={'length': 1, 'modes': ['car'], 'freespeed': 1})
    n.add_link('link_2', 'node_1', 'node_2', attribs={'length': 1, 'modes': ['bus'], 'freespeed': 1})
    n.add_link('link_3', 'node_2', 'node_3', attribs={'length': 1, 'modes': ['car'], 'freespeed': 1})
    n.add_link('link_4', 'node_3', 'node_4', attribs={'length': 1, 'modes': ['car'], 'freespeed': 1})
    n.add_link('link_5', 'node_1', 'node_4', attribs={'length': 1, 'modes': ['bus'], 'freespeed': 1})
    n.add_link('link_6', 'node_4', 'node_5', attribs={'length': 1, 'modes': ['car'], 'freespeed': 1})
    n.add_link('link_7', 'node_5', 'node_6', attribs={'length': 1, 'modes': ['car'], 'freespeed': 1})
    n.add_link('link_8', 'node_6', 'node_7', attribs={'length': 1, 'modes': ['car'], 'freespeed': 1})
    n.add_link('link_9', 'node_7', 'node_8', attribs={'length': 1, 'modes': ['car'], 'freespeed': 1})
    n.add_link('link_10', 'node_8', 'node_9', attribs={'length': 1, 'modes': ['car'], 'freespeed': 1})

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
    assert network.schedule.stop('stop_1').has_linkRefId
    assert network.schedule.stop('stop_1').linkRefId == 'link_5'
    assert network.schedule.stop('stop_2').has_linkRefId
    assert network.schedule.route('service_1_route_1').route
    if network.schedule.stop('stop_2').linkRefId == 'link_6':
        assert network.schedule.route('service_1_route_1').route == ['link_5', 'link_6']
    elif network.schedule.stop('stop_2').linkRefId == 'link_7':
        assert network.schedule.route('service_1_route_1').route == ['link_5', 'link_6', 'link_7']
    else:
        raise AssertionError

    assert network.schedule.stop('stop_3').has_linkRefId
    assert network.schedule.stop('stop_3').linkRefId == 'link_8'
    assert network.schedule.stop('stop_2').has_linkRefId
    assert network.schedule.route('service_1_route_2').route
    if network.schedule.stop('stop_2').linkRefId == 'link_6':
        assert network.schedule.route('service_1_route_2').route == ['link_6', 'link_7', 'link_8']
    elif network.schedule.stop('stop_2').linkRefId == 'link_7':
        assert network.schedule.route('service_1_route_2').route == ['link_7', 'link_8']
    else:
        raise AssertionError


def test_find_routes_for_schedule(mocker, network):
    mocker.patch.object(spatial, 'find_closest_nodes',
                        side_effect=[['node_5', 'node_6'], ['node_7', 'node_8'], ['node_1', 'node_2'], []])
    mod_schedule.find_routes_for_schedule(network, 30, solver='glpk')
    assert_correct_routing_for_service_1(network)


def test_find_routes_for_service(mocker, network):
    mocker.patch.object(spatial, 'find_closest_nodes',
                        side_effect=[['node_5', 'node_6'], ['node_7', 'node_8'], ['node_1', 'node_2']])
    mod_schedule.find_routes_for_service(network.graph, network.schedule['service_1'], 30, solver='glpk')
    assert_correct_routing_for_service_1(network)


def test_find_route_for_route(mocker, network):
    mocker.patch.object(spatial, 'find_closest_nodes',
                        side_effect=[['node_5', 'node_6'], ['node_1', 'node_2']])

    r = network.schedule.route('service_1_route_1')

    mod_schedule.find_route_for_route(network.graph, r, 30, solver='glpk')

    assert r.route
    assert r.route == ['link_5', 'link_6']
    assert r.stop('stop_1').has_linkRefId
    assert r.stop('stop_1').linkRefId == 'link_5'
    assert r.stop('stop_2').has_linkRefId
    assert r.stop('stop_2').linkRefId == 'link_6'


def test_find_route_when_one_stop_doesnt_have_nodes_to_snap_to():
    pass


def test_find_route_when_one_stop_doesnt_have_any_shortest_paths_joing_other_stops_closest_nodes():
    pass


def test_find_route_when_service_has_two_separate_edges_but_one_stop_has_common_closest_nodes(mocker, network):
    mocker.patch.object(
        spatial,
        'find_closest_nodes',
        side_effect=[['node_1', 'node_2'], ['node_5', 'node_6'], ['node_5', 'node_6'], ['node_1', 'node_2']])

    for u, v, data in network.graph.edges(data=True):
        network.add_link(network.generate_index_for_edge(), u=v, v=u, attribs=data)

    network.schedule = Schedule(epsg='epsg:27700',
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
                                   stops=[Stop(epsg='epsg:27700', id='stop_3', x=2, y=2.5),
                                          Stop(epsg='epsg:27700', id='stop_4', x=1, y=2.5)],
                                   trips={'trip_1': '16:30:00'},
                                   arrival_offsets=['00:00:00', '00:02:00'],
                                   departure_offsets=['00:00:00', '00:03:00']
                                   )
                         ])])
    mod_schedule.find_routes_for_schedule(network, 30, solver='glpk')

    assert network.schedule.is_valid_schedule()

