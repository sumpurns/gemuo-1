#!/usr/bin/python

import sys
from uo.entity import *
import uo.packets as p
from gemuo.entity import Item
from gemuo.simple import SimpleClient
from gemuo.engine import Engine
from gemuo.engine.messages import PrintMessages
from gemuo.engine.util import FinishCallback, Delayed, DelayedCallback, Fail
from gemuo.engine.restock import drop_into
from gemuo.engine.menu import MenuResponse
from gemuo.engine.items import OpenContainer

def find_box_at(world, x, y):
    for e in world.iter_entities_at(x, y):
        if isinstance(e, Item) and e.item_id in ITEMS_LARGE_CRATE:
            return e
    return None

def find_restock_box(world):
    """Find the large crate one tile north of the player.  It is used
    for restocking."""
    return find_box_at(world, world.player.position.x, world.player.position.y - 1)

def TakeLogs(client, box, amount=180):
    world = client.world

    logs = world.find_item_in(box, lambda x: x.item_id in ITEMS_LOGS)
    if logs is None:
        print "No logs in box"
        return Fail(client)

    drop_into(client, logs, world.backpack(), amount)
    return Delayed(client, 1)

def PutBoards(client, box):
    world = client.world

    boards = world.find_item_in(world.backpack(), lambda x: x.item_id in ITEMS_BOARDS)
    if boards is None:
        print "No boards"
        return Fail(client)

    drop_into(client, boards, box)
    return Delayed(client, 1)

class MakeBoards(Engine):
    def __init__(self, client):
        Engine.__init__(self, client)

        tool = client.world.find_item_in(client.world.backpack(), lambda x: x.item_id in ITEMS_CARPENTRY_TOOLS)
        if tool is None:
            print "No tool"
            self._failure()
            return

        client.send(p.Use(tool.serial))

        FinishCallback(client, MenuResponse(client, ('Other',
                                                     'board: 1 Logs')),
                       self._responded)

    def _responded(self, success):
        if success:
            DelayedCallback(self._client, 10, self._delay)
        else:
            self._failure()

    def _delay(self):
        self._success()

class AutoBoards(Engine):
    def __init__(self, client, restock_box):
        Engine.__init__(self, client)
        self.restock_box = restock_box
        self._take_logs(True)

    def _take_logs(self, success):
        if not success:
            self._failure()
            return

        client = self._client
        FinishCallback(client, TakeLogs(client, restock_box), self._make_boards)

    def _make_boards(self, success):
        if not success:
            self._failure()
            return

        client = self._client
        FinishCallback(client, MakeBoards(client), self._put_boards)

    def _put_boards(self, success):
        if not success:
            self._failure()
            return

        client = self._client
        FinishCallback(client, PutBoards(client, restock_box), self._take_logs)

client = SimpleClient()

PrintMessages(client)

restock_box = find_restock_box(client.world)
if restock_box is None:
    print "No box"
    sys.exit(1)

client.until(OpenContainer(client, restock_box).finished)
client.until(Delayed(client, 1).finished)
client.until(OpenContainer(client, client.world.backpack()).finished)
client.until(Delayed(client, 1).finished)

client.until(AutoBoards(client, restock_box).finished)