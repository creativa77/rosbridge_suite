#!/usr/bin/env python
import rospy
import signal


from tornado.websocket import websocket_connect
from tornado.ioloop import IOLoop

from datetime import timedelta

from rosbridge_library.rosbridge_protocol import RosbridgeProtocol


PING_TIMEOUT = 15

ws = None
protocol = None

# WebsocketClientTornado
#
# Class that handles the connection using websocket from Tornado Project.
# More info:
# http://www.tornadoweb.org/en/stable/websocket.html#client-side-support
# Example code: http://www.seismicportal.eu/realtime.html


class WebsocketClientTornado():

    conn = None
    keepalive = None

    def __init__(self, uri):
        self.uri = uri
        self.doconn()

    def doconn(self):
        rospy.loginfo("trying connection to %s" % (self.uri,))
        w = websocket_connect(self.uri)
        rospy.loginfo("connected, waiting for messages")
        w.add_done_callback(self.wsconnection_cb)

    def dokeepalive(self):
        stream = self.conn.protocol.stream
        if not stream.closed():
            self.keepalive = stream.io_loop.add_timeout(
                timedelta(seconds=PING_TIMEOUT),
                self.dokeepalive)
            self.conn.protocol.write_ping("")
        else:
            rospy.logerror("Stream closed")
            self.keepalive = None  # should never happen

    def wsconnection_cb(self, conn):
        self.conn = conn.result()
        self.conn.on_message = self.message
        self.send_message('{"op":"proxy"}')
        self.keepalive = IOLoop.instance().add_timeout(
            timedelta(seconds=PING_TIMEOUT),
            self.dokeepalive)

    def message(self, _message):
        rospy.logdebug("Msg received: [%s]" % _message)
        protocol.incoming(_message)

    def close(self):
        rospy.loginfo('connection closed')
        if self.keepalive is not None:
            keepalive = self.keepalive
            self.keepalive = None
            IOLoop.instance().remove_timeout(keepalive)
        self.doconn()

    def send_message(self, _message):
        self.conn.write_message(_message)
        rospy.logdebug("Msg sent: [%s]" % _message)


if __name__ == "__main__":
    try:
        rospy.init_node("rosbridge_websocket_client")

        io_loop = IOLoop.instance()
        signal.signal(signal.SIGTERM, io_loop.stop)

        protocol = RosbridgeProtocol(0)

        # Connect with server
        server_uri = rospy.get_param("~server_uri")
        ws = WebsocketClientTornado(server_uri)

        protocol.outgoing = ws.send_message

        # Loop
        IOLoop.instance().start()

    except rospy.ROSInterruptException:
        IOLoop.instance().stop()
