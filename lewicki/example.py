from typing import NoReturn

from actors import ActorSystem, BaseActor
from messages import Message


class SimpleActorSystem(ActorSystem):

	def __init__(self):
		super().__init__()

	def run(self) -> NoReturn:
		# Populate the queues with initial messages
		for i, (actor, inbox) in enumerate(self.outbox.items()):
			msg = Message(i, sender=self.name, receiver=actor)
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
			msg = Message(msg.data, sender=self.name, receiver=name)
			self.send(msg)
		self.count += 1

	def should_stop(self) -> bool:
		return self.count > 1


if __name__ == '__main__':
	a1 = SimpleActor()
	a2 = SimpleActor()
	a3 = SimpleActor()
	system = SimpleActorSystem()
	system.connect(a1, a2, a3)
	system.run()
