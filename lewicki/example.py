from typing import NoReturn

from actors import ActorSystem, BaseActor
from messages import Message


class SimpleActorSystem(ActorSystem):

	def __init__(self):
		super().__init__()

	def run(self) -> NoReturn:
		# Populate the queues with initial messages
		for i, (actor, inbox) in enumerate(self.outbox.items()):
			msg = Message(self.name, actor, i)
			self.send(msg)
		super().run()


class SimpleActor(BaseActor):
	__slots__ = ('count',)

	def __init__(self):
		super().__init__()
		self.count = 0

	def on_next(self, msg: Message) -> NoReturn:
		print(msg)
		for name, actor in self.outbox.items():
			msg = Message(self.name, name, msg.data)
			self.send(msg)
		self.count += 1

	def should_stop(self) -> bool:
		stop = self.count > 1
		return stop


if __name__ == '__main__':
	a1 = SimpleActor()
	a2 = SimpleActor()
	a3 = SimpleActor()
	system = SimpleActorSystem()
	system.connect(a1, a2, a3)
	system.run()
