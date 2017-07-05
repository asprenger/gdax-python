#
# gdax/WebsocketClient.py
# Daniel Paquin
#
# Template object to receive messages from the gdax Websocket Feed

from __future__ import print_function
import json
import hmac
import hashlib
import time
import base64

from threading import Thread
from websocket import create_connection, WebSocketConnectionClosedException

class WebsocketClient(object):
    def __init__(self, url="wss://ws-feed.gdax.com", products=None, message_type="subscribe", 
                 api_key=None, api_secret=None, passphrase=None):
        self.url = url
        self.products = products
        self.type = message_type
        self.stop = False
        self.ws = None
        self.thread = None
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase

    def start(self):
        def _go():
            self._connect()
            self._listen()

        self.on_open()
        self.thread = Thread(target=_go)
        self.thread.daemon = True
        self.thread.start()

    def _connect(self):
        if self.products is None:
            self.products = ["BTC-USD"]
        elif not isinstance(self.products, list):
            self.products = [self.products]

        if self.url[-1] == "/":
            self.url = self.url[:-1]

        self.ws = create_connection(self.url)

        self.stop = False
        sub_params = {'type': 'subscribe', 'product_ids': self.products}

        if self.api_key and self.api_secret and self.passphrase:
            sig = self._sign_request('GET', '/users/self')
            sub_params.update(sig)

        self.ws.send(json.dumps(sub_params))
        if self.type == "heartbeat":
            sub_params = {"type": "heartbeat", "on": True}
            self.ws.send(json.dumps(sub_params))

    def _sign_request(self, method, path):
        timestamp = str(time.time())
        message = timestamp + method + path
        message = message.encode('ascii')
        hmac_key = base64.b64decode(self.api_secret)
        signature = hmac.new(hmac_key, message, hashlib.sha256)
        signature_b64 = base64.b64encode(signature.digest())
        return {
            'signature': signature_b64,
            'timestamp': timestamp,
            'key': self.api_key,
            'passphrase': self.passphrase
            }


    def _listen(self):
        while not self.stop:
            try:
                msg = json.loads(self.ws.recv())
            except Exception as e:
                self.on_error(e)
            else:
                self.on_message(msg)

    def close(self):
        if not self.stop:
            if self.type == "heartbeat":
                self.ws.send(json.dumps({"type": "heartbeat", "on": False}))
            self.on_close()
            self.stop = True
            try:
                if self.ws:
                    self.ws.close()
            except WebSocketConnectionClosedException as e:
                pass

    def on_open(self):
        print("-- Subscribed! --\n")

    def on_close(self):
        print("\n-- Socket Closed --")

    def on_message(self, msg):
        print(msg)

    def on_error(self, e):
        return

if __name__ == "__main__":
    import gdax
    import time

    class MyWebsocketClient(gdax.WebsocketClient):
        def on_open(self):
            self.url = "wss://ws-feed.gdax.com/"
            self.products = ["BTC-USD", "ETH-USD"]
            self.message_count = 0
            print("Let's count the messages!")

        def on_message(self, msg):
            if 'price' in msg and 'type' in msg:
                print("Message type:", msg["type"], "\t@ %.3f" % float(msg["price"]))
            self.message_count += 1

        def on_close(self):
            print("-- Goodbye! --")

    wsClient = MyWebsocketClient()
    wsClient.start()
    print(wsClient.url, wsClient.products)
    # Do some logic with the data
    while wsClient.message_count < 500:
        print("\nMessageCount =", "%i \n" % wsClient.message_count)
        time.sleep(1)

    wsClient.close()
