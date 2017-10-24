"""kytos/flow_manager NApp installs, lists and deletes switch flows."""
import json

from flask import request
from kytos.core import KytosEvent, KytosNApp, log, rest

from napps.kytos.of_core.v0x01.flow import Flow as Flow10
from napps.kytos.of_core.v0x04.flow import Flow as Flow13

class Main(KytosNApp):
    """Main class to be used by Kytos controller."""

    def setup(self):
        """Replace the 'init' method for the KytosApp subclass.

        The setup method is automatically called by the run method.
        Users shouldn't call this method directly.
        """
        log.debug("flow-manager starting")

    def execute(self):
        """Run once on NApp 'start' or in a loop.

        The execute method is called by the run method of KytosNApp class.
        Users shouldn't call this method directly.
        """
        pass

    def shutdown(self):
        """Shutdown routine of the NApp."""
        log.debug("flow-manager stopping")

    @rest('v1/flows')
    @rest('v1/flows/<dpid>')
    def list(self, dpid=None):
        """Retrieve all flows from a switch identified by dpid.

        If no dpid is specified, return all flows from all switches.
        """
        dpids = [dpid] if dpid else self.controller.switches
        switches = [self.controller.get_switch_by_dpid(dpid) for dpid in dpids]

        switch_flows = {}

        for switch in switches:
            flows_dict = [flow.as_dict() for flow in switch.flows]
            switch_flows[switch.dpid] = {'flows': flows_dict}

        return json.dumps(switch_flows)

    @rest('v1/flows', methods=['POST'])
    @rest('v1/flows/<dpid>', methods=['POST'])
    def add(self, dpid=None):
        """Install new flows in the switch identified by dpid.

        If no dpid is specified, install flows in all switches.
        """
        return self._send_flow_mods_from_request(request, dpid, "add")

    @rest('v1/delete', methods=['POST'])
    @rest('v1/delete/<dpid>', methods=['POST'])
    def delete(self, dpid=None):
        """Delete existing flows in the switch identified by dpid.

        If no dpid is specified, delete flows from all switches.
        """
        return self._send_flow_mods_from_request(request, dpid, "delete")

    def _send_flow_mods_from_request(self, request, dpid, command):
        flows_dict = request.get_json()

        if dpid:
            switches = [self.controller.get_switch_by_dpid(dpid)]
        else:
            switches = self.controller.switches.values()

        for switch in switches:
            serializer = self._get_flow_serializer(switch)
            for flow_dict in flows_dict:
                flow = serializer.from_dict(flow_dict, switch)
                if command == "delete":
                    flow_mod = flow.as_delete_flow_mod()
                elif command == "add":
                    flow_mod = flow.as_add_flow_mod()
                self._send_flow_mod(flow.switch, flow_mod)

            self._send_napp_event(switch, flow, command)

        return json.dumps({"response": "FlowMod Messages Sent"}), 202

    def _send_flow_mod(self, switch, flow_mod):
        event_name = 'kytos/flow_manager.messages.out.ofpt_flow_mod'

        content = {'destination': switch.connection,
                   'message': flow_mod}

        event = KytosEvent(name=event_name, content=content)
        self.controller.buffers.msg_out.put(event)


    def _send_napp_event(self, switch, flow, command):
        """Send an Event to other apps informing about a FlowMod."""
        if command == 'add':
            name = 'kytos/flow_manager.flow.added'
        elif command == 'delete':
            name = 'kytos/flow_manager.flow.removed'
        content = {'datapath': switch,
                   'flow': flow}
        event_app = KytosEvent(name, content)
        self.controller.buffers.app.put(event_app)

    def _get_flow_serializer(self, switch):
        """Return the serializer with for the switch OF protocol version."""
        version = switch.connection.protocol.version
        return Flow10 if version == 0x01 else Flow13
