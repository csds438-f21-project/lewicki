import itertools
import uuid
from abc import ABC, abstractmethod
from multiprocessing import Process, Queue
from typing import (
    Hashable, MutableMapping, MutableSequence, NoReturn, Optional
)

from lewicki.messages import Message, MessageKind


class BaseActor(ABC):
    """An actor as defined in the actor-based model of computing.

    Attributes:
        name: A hashable value that identifies the actor.
        inbox: A buffer that stores messages received from other actors.
        outbox: A mapping from actor names to their inboxes.
    """

    __slots__ = ('name', 'inbox', 'outbox')

    def __init__(self, name: Optional[Hashable] = None):
        super().__init__()
        self.name = name or str(uuid.uuid4().time_low)
        self.inbox: Queue = Queue()
        self.outbox: MutableMapping[Hashable, Queue] = {}

    @abstractmethod
    def on_next(self, msg: Message) -> NoReturn:
        """Processes a message."""
        raise NotImplementedError

    @abstractmethod
    def should_stop(self) -> bool:
        """Returns True if the actor should terminate."""
        raise NotImplementedError

    def run(self) -> NoReturn:
        """Initiates the actor."""
        while not self.should_stop():
            msg = self.receive()
            if self.should_ignore(msg):
                pass
            elif msg.kind == MessageKind.DEFAULT:
                self.on_next(msg)
            elif msg.kind == MessageKind.CALL:
                self.handle_call(msg)
            elif msg.kind == MessageKind.RETURN:
                self.handle_return(msg)
            elif msg.kind == MessageKind.ACK:
                self.handle_ack(msg)
            elif msg.kind == MessageKind.SET:
                self.handle_set(msg)
            else:
                pass

    def handle_call(self, msg: Message) -> NoReturn:
        """Handle CALL Message."""
        data = msg.data
        method = getattr(self, data['name'])
        args, kwargs = data.get('args'), data.get('kwargs')

        # TODO is there a way to make this better?
        # Call method with args and kwargs, if any
        if args is not None and kwargs is not None:
            return_data = method(*args, **kwargs)
        elif args is not None:
            return_data = method(*args)
        elif kwargs is not None:
            return_data = method(**kwargs)
        else:
            return_data = method()

        # Send a message with returned values
        receiver = msg.sender
        if receiver and data.get('return', True):
            return_msg = Message(
                return_data,
                sender=self.name,
                receiver=receiver,
                kind=MessageKind.RETURN,
                prev_id=msg.id)
            self.send(return_msg)

    def handle_return(self, msg: Message) -> NoReturn:
        """Handle RETURN Message."""
        pass

    def handle_ack(self, msg: Message) -> NoReturn:
        """Handle ACK Message."""
        pass

    def handle_set(self, msg: Message) -> NoReturn:
        """Handle SET Message."""
        data = msg.data
        setattr(self, data['name'], data['value'])

    def should_ignore(self, msg: Message) -> bool:
        """Returns True if the actor should ignore the received message."""
        return False

    def send(self, *msgs: Message) -> NoReturn:
        """Sends messages to other actors."""
        for m in msgs:
            self.outbox[m.receiver].put(m, block=True)

    def receive(self) -> Message:
        """Receives a message from another actor."""
        return self.inbox.get(block=True)

    def connect(self, *actors: 'BaseActor') -> NoReturn:
        """Enables this actor to send messages to other actors."""
        self.outbox.update((a.name, a.inbox) for a in actors)

    def disconnect(self, *actors: 'BaseActor') -> NoReturn:
        """Disables this actor from sending messages to other actors."""
        for a in actors:
            self.outbox.pop(a.name, None)

    def __repr__(self):
        return f'{self.__class__.__name__}(name={self.name})'


class ActorSystem(BaseActor):
    """The root-level actor that manages a collection of actors.

    Attributes:
        actors: A sequence of actors that the system manages.
    """

    __slots__ = ('actors', '_actors')

    def __init__(self, name: Optional[Hashable] = None):
        super().__init__(name=name)
        self.actors: MutableSequence[BaseActor] = []
        self._actors: MutableMapping[Hashable, Process] = {}

    def connect(self, *actors: 'BaseActor') -> NoReturn:
        """Fully connects all actors to each other and the system."""
        super().connect(*actors)
        self.actors.extend(actors)
        self._actors.update((a.name, Process(target=a.run)) for a in actors)

        for a in actors:
            a.connect(self)
        for a1, a2 in itertools.combinations(actors, r=2):
            a1.connect(a2)
            a2.connect(a1)

    def run(self) -> NoReturn:
        """Initiates all actor processes and waits for their termination."""
        for a in self._actors.values():
            a.start()
        super().run()
        for a in self._actors.values():
            a.join()

    def on_next(self, msg: Message) -> NoReturn:
        # No-op
        pass

    def should_stop(self) -> bool:
        # No-op
        return True
