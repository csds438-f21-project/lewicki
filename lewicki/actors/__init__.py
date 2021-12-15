import itertools
import uuid
from abc import ABC, abstractmethod
from multiprocessing import Process, Queue
from typing import (
    Any, Hashable, MutableMapping, MutableSequence, NoReturn, Optional
)

from ..messages import Message, MessageKind


class BaseActor(ABC):
    """An actor as defined in the actor-based model of computing.

    Attributes:
        name: A hashable otherwise that identifies the actor.
        inbox: A buffer that stores messages received from other actors.
        outbox: A mapping from actor names to their inboxes.
    """
    __slots__ = ('name', 'inbox', 'outbox')

    def __init__(
            self,
            name: Optional[Hashable] = None,
            inbox: Optional[Any] = None):
        super().__init__()
        self.name = self._else(name, str(uuid.uuid4().time_low))
        self.inbox = self._else(inbox, Queue())
        self.outbox = {}

    @staticmethod
    def _else(optional, otherwise):
        return optional if optional is not None else otherwise

    @abstractmethod
    def on_next(self, msg: Any) -> NoReturn:
        """Processes a message."""
        pass

    @abstractmethod
    def should_stop(self) -> bool:
        """Returns True if the actor should terminate."""
        pass

    def run(self) -> Any:
        """Initiates the actor."""
        stop, receive, on_next = self.should_stop, self.receive, self.on_next
        while not stop():
            on_next(receive())

    @abstractmethod
    def send(self, *msgs: Any) -> NoReturn:
        """Sends messages to other actors."""
        pass

    def receive(self) -> Any:
        """Receives a message from another actor."""
        return self.inbox.get(block=True)

    def connect(self, *actors: 'BaseActor') -> NoReturn:
        """Enables this actor to send messages to other actors."""
        self.outbox.update((a.name, a.inbox) for a in actors)

    def disconnect(self, *actors: 'BaseActor') -> NoReturn:
        """Disables this actor from sending messages to other actors."""
        pop = self.outbox.pop
        for a in actors:
            pop(a.name, None)

    def __repr__(self):
        return f'{self.__class__.__name__}(name={self.name})'


class MessageActor(BaseActor):
    """An base actor with default logic for handling messages.

    Attributes:
        attrs: A mapping to maintain any mutable state.
    """

    _EMPTY_ARGS = ()
    _EMPTY_KWARGS = {}

    __slots__ = ('attrs',)

    def __init__(self, name: Optional[Hashable] = None):
        super().__init__(name)
        self.attrs: MutableMapping[Hashable, Any] = {}

    def on_next(self, msg: Message) -> NoReturn:
        """Processes a message."""
        pass

    def should_stop(self) -> bool:
        """Returns True if the actor should terminate."""
        pass

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

    def handle_call(self, msg: Message) -> NoReturn:
        """Handle CALL Message."""
        # Prepare method call and get return otherwise
        data = msg.data
        method = self.attrs[data['name']]
        args = data.get('args', self._EMPTY_ARGS)
        kwargs = data.get('kwargs', self._EMPTY_KWARGS)
        return_data = method(*args, **kwargs)

        # Send a message with returned otherwise if requested
        if msg.sender and data.get('return', True):
            return_msg = Message(
                return_data,
                sender=self.name,
                receiver=msg.sender,
                kind=MessageKind.RETURN,
                prev_id=msg.id)
            self.send(return_msg)

    def send(self, *msgs: Any) -> NoReturn:
        """Sends messages to other actors."""
        for m in msgs:
            self.outbox[m.receiver].put(m, block=True)

    def handle_return(self, msg: Message) -> NoReturn:
        """Handle RETURN Message."""
        pass

    def handle_ack(self, msg: Message) -> NoReturn:
        """Handle ACK Message."""
        pass

    def handle_set(self, msg: Message) -> NoReturn:
        """Handle SET Message."""
        data = msg.data
        self.attrs[data['name']] = data['value']

    def should_ignore(self, msg: Message) -> bool:
        """Returns True if the actor should ignore the received message."""
        return False


class BaseActorSystem(BaseActor, ABC):
    """The root-level actor that manages a collection of actors.

    Attributes:
        actors: A sequence of actors that the system manages.
    """
    __slots__ = ('actors', '_actors')

    def __init__(
            self,
            name: Optional[Hashable] = None,
            inbox: Optional[Any] = None):
        super().__init__(name, inbox)
        self.actors: MutableSequence[BaseActor] = []
        self._actors: MutableMapping[Hashable, Process] = {}

    def connect(self, *actors: 'BaseActor', complete: bool = True) -> NoReturn:
        """Fully connects all actors to each other and the system."""
        super().connect(*actors)
        self.actors.extend(actors)
        self._actors.update((a.name, Process(target=a.run)) for a in actors)

        for a in actors:
            a.connect(self)
        if complete:
            self._make_complete(*actors)

    @staticmethod
    def _make_complete(*actors: 'BaseActor') -> NoReturn:
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

    def on_next(self, msg: Any) -> NoReturn:
        # No-op
        pass

    def should_stop(self) -> bool:
        # No-op
        return True


class MessageActorSystem(MessageActor, ABC):
    """An actor system that runs as a MessageActor."""

    __slots__ = ('actors', '_actors')

    def __init__(
            self,
            name: Optional[Hashable] = None):
        super().__init__(name)
        self.actors: MutableSequence[BaseActor] = []
        self._actors: MutableMapping[Hashable, Process] = {}

    def connect(self, *actors: 'MessageActor', complete: bool = True) -> NoReturn:
        """Fully connects all actors to each other and the system."""
        super().connect(*actors)
        self.actors.extend(actors)
        self._actors.update((a.name, Process(target=a.run)) for a in actors)

        for a in actors:
            a.connect(self)
        if complete:
            self._make_complete(*actors)

    @staticmethod
    def _make_complete(*actors: 'MessageActor') -> NoReturn:
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

    def on_next(self, msg: Any) -> NoReturn:
        # No-op
        pass

    def should_stop(self) -> bool:
        # No-op
        return True
