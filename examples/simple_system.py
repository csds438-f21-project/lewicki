import sys
from typing import NoReturn

sys.path.append('../lewicki')

from lewicki.actors import MessageActorSystem, MessageActor
from lewicki.messages import Message


class SimpleActorSystem(MessageActorSystem):

    def __init__(self, name: str):
        super().__init__(name=name)

    def run(self) -> NoReturn:
        # Populate the queues with initial messages
        for i, (actor, inbox) in enumerate(self.outbox.items()):
            msg = Message(i, sender=self.name, receiver=actor)
            self.send(msg)
        super().run()


class SimpleActor(MessageActor):
    __slots__ = ('count',)

    def __init__(self, name: str):
        super().__init__(name=name)
        self.count = 0

    def on_next(self, msg: Message) -> NoReturn:
        print(msg)
        for name, actor in self.outbox.items():
            msg = Message(msg.data, sender=self.name, receiver=name,
                          prev_id=msg.id)
            self.send(msg)
        self.count += 1

    def should_stop(self) -> bool:
        return self.count > 1


if __name__ == '__main__':
    actors = [SimpleActor(name=f'a{a}') for a in range(4)]
    system = SimpleActorSystem(name='sys')
    system.connect(*actors)
    system.run()
