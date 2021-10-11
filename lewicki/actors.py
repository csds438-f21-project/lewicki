import itertools
import uuid
from abc import ABC, abstractmethod
from multiprocessing import Process, Queue
from typing import (
	Hashable, MutableMapping, MutableSequence, NoReturn, Optional
)

from messages import Message


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

	def run(self) -> NoReturn:
		"""Initiates the actor."""
		while not self.should_stop():
			msg = self.receive()
			self.on_next(msg)

	@abstractmethod
	def should_stop(self) -> bool:
		"""Returns True if the actor should terminate."""
		pass

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

	@abstractmethod
	def on_next(self, msg: Message) -> NoReturn:
		"""Processes a message."""
		pass

	def __repr__(self):
		return f'{self.__class__.__name__}(name={self.name})'


class ActorSystem(BaseActor):
	"""The root-level actor that manages a collection of actors.

	Attributes:
		actors: A sequence of actors that the system manages.
	"""

	__slots__ = ('actors', '_actors')

	def __init__(self):
		super().__init__()
		self.actors: MutableSequence[BaseActor] = []
		self._actors: MutableMapping[Hashable, Process] = {}

	def connect(self, *actors: 'BaseActor') -> NoReturn:
		"""Fully connects all actors to each other and the system."""
		super().connect(*actors)
		self.actors.extend(actors)
		self._actors.update((a.name, Process(target=a.run)) for a in actors)
		for a1, a2 in itertools.combinations(actors, r=2):
			a1.connect(a2)
			a2.connect(a1)

	def run(self) -> NoReturn:
		"""Initiates all actors and waits for their termination."""
		for a in self._actors.values():
			a.start()
		for a in self._actors.values():
			a.join()

	def on_next(self, msg: Message) -> NoReturn:
		# No-op
		pass

	def should_stop(self) -> bool:
		# No-op
		return False
