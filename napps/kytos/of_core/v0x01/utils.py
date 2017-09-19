"""Utilities module for of_core OpenFlow v0x01 operations"""
from kytos.core.switch import Interface

from napps.kytos.of_core.utils import emit_message_out

from pyof.v0x01.controller2switch.common import FlowStatsRequest
from pyof.v0x01.controller2switch.stats_request import StatsRequest, StatsTypes
from pyof.v0x01.symmetric.echo_request import EchoRequest


def update_flow_list(controller, switch):
    """Method responsible for request stats of flow to switches.

    Args:
        controller(:class:`~kytos.core.controller.Controller`):
            the controller beeing used.
        switch(:class:`~kytos.core.switch.Switch`):
            target to send a stats request.
    """
    body = FlowStatsRequest()
    stats_request = StatsRequest(
        body_type=StatsTypes.OFPST_FLOW,
        body=body)
    # req.pack()
    emit_message_out(controller, switch.connection, stats_request)


def handle_features_reply(controller, event):
    """Handle OF v0x01 features_reply message events.

    This is the end of the Handshake workflow of the OpenFlow Protocol.

    Parameters:
        controller (Controller): Controller beeing used.
        event (KytosEvent): Event with features reply message.
    """

    connection = event.source
    features_reply = event.content['message']
    dpid = features_reply.datapath_id.value

    switch = controller.get_switch_or_create(dpid=dpid,
                                             connection=connection)

    for port in features_reply.ports:
        interface = Interface(name=port.name.value,
                              address=port.hw_addr.value,
                              port_number=port.port_no.value,
                              switch=switch,
                              state=port.state.value,
                              features=port.curr)
        switch.update_interface(interface)

    switch.update_features(features_reply)

    return switch

def send_echo(controller, switch):
    """Send echo request to a datapath.

    Keep the connection alive through symmetric echoes.
    """
    echo = EchoRequest(data=b'kytosd_10')
    emit_message_out(controller, switch.connection, echo)
