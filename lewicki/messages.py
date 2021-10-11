from typing import Any, Hashable, Optional


class Message:
	__slots__ = ('sender', 'receiver', 'kind', 'data')

	def __init__(
			self,
			data: Any,
			*,
			receiver: Hashable,
			sender: Optional[Hashable] = None,
			kind: Optional[Hashable] = None):
		self.data = data
		self.receiver = receiver
		self.sender = sender
		self.kind = kind

	def __repr__(self):
		cls = f'{self.__class__.__name__}'
		sender = f'sender={self.sender}'
		receiver = f'receiver={self.receiver}'
		kind = f'kind={self.kind}'
		data = f'data={self.data}'
		return f'{cls}({sender}, {receiver}, {kind}, {data})'
