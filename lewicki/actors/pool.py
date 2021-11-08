from typing import Any, Callable, NoReturn, Sequence

from . import MessageActor, MessageActorSystem
from ..messages import Message, MessageKind


class ActorPool:
    """Manages a fixed set of actors behind simple  interface"""

    __slots__ = ('processes',)

    def __init__(self, processes: int):
        self.processes = processes

    def map(self, func: Callable, iterable: Sequence[Any]):
        num_actors = min(len(iterable), self.processes)
        actors = (MapActor() for _ in range(num_actors))
        system = MapActorSystem(func, iterable)
        system.connect(*actors)
        return system.run()


class MapActor(MessageActor):
    """An actor specially designed to work for ActorPool.map"""

    def __init__(self):
        super().__init__()
        self.attrs['_stop'] = False

    def should_stop(self) -> bool:
        return self.attrs['_stop']

    def on_next(self, msg: Message) -> NoReturn:
        # Function calls are handled by run
        pass


class MapActorSystem(MessageActorSystem):
    """An MessageActorSystem specially designed to work for ActorPool.map"""

    __slots__ = ('func', 'iterable', 'remaining_items', 'result_map', 'result')

    def __init__(self, func: Callable, iterable: Sequence[Any]):
        super().__init__()
        self.func = func
        self.iterable = iter(enumerate(iterable))

        self.remaining_items = len(iterable)
        self.result_map = {}
        self.result = [None] * self.remaining_items

    def connect(self, *actors: 'MessageActor') -> NoReturn:
        super().connect(*actors, complete=False)

    def run(self) -> Any:
        # Prepare each actor
        for actor in self.outbox:
            # Make function available to actor
            msg1 = Message(
                {'name': '_func', 'value': self.func},
                receiver=actor,
                kind=MessageKind.SET)

            # Send first value to each actor
            idx, value = next(self.iterable)
            msg2 = Message(
                {'name': '_func', 'args': [value]},
                sender=self.name,
                receiver=actor,
                kind=MessageKind.CALL)
            self.send(msg1, msg2)

            # Save state
            self.result_map[msg2.id] = idx

        # Start actors
        super().run()

        return self.result

    def handle_return(self, msg: Message) -> NoReturn:
        # Place value in result and update state
        id = msg.prev_id
        value_idx = self.result_map[id]
        del self.result_map[id]
        self.result[value_idx] = msg.data
        self.remaining_items -= 1

        try:
            # Assign more work if available
            idx, value = next(self.iterable)
            msg = Message(
                {'name': '_func', 'args': [value]},
                sender=self.name,
                receiver=msg.sender,
                kind=MessageKind.CALL)
            self.result_map[msg.id] = idx
        except StopIteration:
            # Tell actor to stop
            msg = Message(
                {'name': '_stop', 'value': True},
                receiver=msg.sender,
                kind=MessageKind.SET)
        self.send(msg)

    def should_stop(self) -> bool:
        return self.remaining_items == 0

    def on_next(self, msg: Message) -> NoReturn:
        pass
