import pytest
from genet.core import Network, Schedule
from genet.schedule_elements import Service, Route, Stop
from genet.utils import routing
import genet.utils.spatial as spatial
from tests.fixtures import assert_semantically_equal


@pytest.fixture()
def network():
    n = Network('epsg:27700')
    n.add_node('node_1', attribs={'x': 1, 'y': 2})
    n.add_node('node_2', attribs={'x': 1, 'y': 3})
    n.add_node('node_3', attribs={'x': 2, 'y': 3})
    n.add_node('node_4', attribs={'x': 2, 'y': 2})
    n.add_node('node_5', attribs={'x': 3, 'y': 2})
    n.add_node('node_6', attribs={'x': 4, 'y': 2})
    n.add_link('link_1', 'node_1', 'node_2', attribs={'length': 1, 'modes': ['car']})
    n.add_link('link_2', 'node_1', 'node_2', attribs={'length': 1, 'modes': ['bus']})
    n.add_link('link_3', 'node_2', 'node_3', attribs={'length': 1, 'modes': ['car']})
    n.add_link('link_4', 'node_3', 'node_4', attribs={'length': 1, 'modes': ['car']})
    n.add_link('link_5', 'node_1', 'node_4', attribs={'length': 1, 'modes': ['bus']})
    n.add_link('link_6', 'node_4', 'node_5', attribs={'length': 1, 'modes': ['car']})
    n.add_link('link_7', 'node_5', 'node_6', attribs={'length': 1, 'modes': ['car']})

    n.schedule = Schedule(epsg='epsg:27700',
                          services=[Service(id='service_1', routes=[
                              Route(id='service_1_route_1',
                                    route_short_name='',
                                    mode='bus',
                                    stops=[Stop(epsg='epsg:27700', id='stop_1', x=1, y=2.5),
                                           Stop(epsg='epsg:27700', id='stop_2', x=2, y=2.5)],
                                    trips={'trip_1': '15:30:00'},
                                    arrival_offsets=['00:00:00', '00:02:00'],
                                    departure_offsets=['00:00:00', '00:03:00']
                                    )
                          ])])
    return n


@pytest.mark.xfail()
def test_showing_unique_schedule_modes(network):
    assert network.schedule_modes() == ['bus']


def test_build_graph_for_maximum_stable_set_problem_with_non_trivial_closest_node_selection_pool(mocker, network):
    mocker.patch.object(spatial, 'find_closest_nodes',
                        side_effect=[['node_1', 'node_2', 'node_3'], ['node_4', 'node_5', 'node_6']])
    network.schedule.id = 'id'
    problem_g, schedule_g = routing.build_graph_for_maximum_stable_set_problem(network.graph, network.schedule, 1)
    assert_semantically_equal(dict(schedule_g.nodes(data=True)), {
        'stop_1': {'x': 1.0, 'y': 2.5, 'lat': 49.76683027967191, 'lon': -7.557148552832129,
                   's2_id': 5205973754090340691, 'closest_nodes': ['node_1', 'node_2', 'node_3']},
        'stop_2': {'x': 2.0, 'y': 2.5, 'lat': 49.76683094462549, 'lon': -7.557134732217642,
                   's2_id': 5205973754090230267, 'closest_nodes': ['node_4', 'node_5', 'node_6']}})
    assert_semantically_equal(list(schedule_g.edges()), [('stop_1', 'stop_2')])
    assert_semantically_equal(dict(problem_g.nodes(data=True)),
                              {'node_1': {'total_path_lengths': 6, 'total_paths': 3, 'stop_id': 'stop_1'},
                               'node_2': {'total_path_lengths': 9, 'total_paths': 3, 'stop_id': 'stop_1'},
                               'node_3': {'total_path_lengths': 6, 'total_paths': 3, 'stop_id': 'stop_1'},
                               'node_4': {'total_path_lengths': 4, 'total_paths': 3, 'stop_id': 'stop_2'},
                               'node_5': {'total_path_lengths': 7, 'total_paths': 3, 'stop_id': 'stop_2'},
                               'node_6': {'total_path_lengths': 10, 'total_paths': 3, 'stop_id': 'stop_2'}})
    assert_semantically_equal(list(problem_g.edges()),
                              [('node_1', 'node_2'), ('node_1', 'node_3'), ('node_2', 'node_3'), ('node_4', 'node_5'),
                               ('node_4', 'node_6'), ('node_5', 'node_6')])


def test_build_graph_for_maximum_stable_set_problem_with_no_path_between_isolated_node(mocker, network):
    mocker.patch.object(spatial, 'find_closest_nodes',
                        side_effect=[['node_1', 'node_2'], ['isolated_node', 'node_5', 'node_6']])
    network.add_node('isolated_node')
    problem_g, schedule_g = routing.build_graph_for_maximum_stable_set_problem(network.graph, network.schedule, 1)
    assert_semantically_equal(dict(schedule_g.nodes(data=True)), {
        'stop_1': {'x': 1.0, 'y': 2.5, 'lat': 49.76683027967191, 'lon': -7.557148552832129,
                   's2_id': 5205973754090340691, 'closest_nodes': ['node_1', 'node_2']},
        'stop_2': {'x': 2.0, 'y': 2.5, 'lat': 49.76683094462549, 'lon': -7.557134732217642,
                   's2_id': 5205973754090230267, 'closest_nodes': ['isolated_node', 'node_5', 'node_6']}})
    assert_semantically_equal(list(schedule_g.edges()), [('stop_1', 'stop_2')])
    assert_semantically_equal(dict(problem_g.nodes(data=True)),
                              {'node_1': {'total_path_lengths': 5, 'total_paths': 2, 'stop_id': 'stop_1'},
                               'node_2': {'total_path_lengths': 7, 'total_paths': 2, 'stop_id': 'stop_1'},
                               'isolated_node': {'total_path_lengths': 0, 'total_paths': 0, 'stop_id': 'stop_2'},
                               'node_5': {'total_path_lengths': 5, 'total_paths': 2, 'stop_id': 'stop_2'},
                               'node_6': {'total_path_lengths': 7, 'total_paths': 2, 'stop_id': 'stop_2'}})
    assert_semantically_equal(list(problem_g.edges()),
                              [('node_1', 'node_2'), ('node_1', 'isolated_node'), ('node_2', 'isolated_node'),
                               ('isolated_node', 'node_5'), ('isolated_node', 'node_6'), ('node_5', 'node_6')])


def test_routing_single_route(mocker, network):
    mocker.patch.object(spatial, 'find_closest_nodes',
                        side_effect=[['node_1', 'node_2'], ['node_5', 'node_6']])
    pass
