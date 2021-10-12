
import uuid
from enum import Enum
from typing import Any, Hashable, Optional

class MessageKind(Enum):
    """Specifies the kind of message sent to an Actor

    DEFAULT: Message contains arbitrary data
    CALL: Message contains method name and arguments as a dict
        {'name': <method_name>, ['args': <args>], ['kwargs': <kwargs>], ['return': True]}
    RETURN: Message contains data in response to a CALL message
    ACK: Message contains no data, acknowledges receipt of previous message
    SET: Message contains varaible name and value as a dict
        {'name': <variable_name>, 'value': <value>}
    """
    DEFAULT = 0
    CALL = 1
    RETURN = 2
    ACK = 3
    SET = 4

class Message:
    __slots__ = ('id', 'previous_id', 'sender', 'receiver', 'kind', 'data')

    def __init__(
            self,
            data: Any,
            *,
            receiver: Hashable,
            sender: Optional[Hashable] = None,
            kind: Optional[Hashable] = MessageKind.DEFAULT,
            previous_id: Optional[Hashable] = None):
        self.data = data
        self.receiver = receiver
        self.sender = sender
        self.kind = kind

        self.id = str(uuid.uuid4().time_low)
        self.previous_id = previous_id

    def __repr__(self):
        cls = f'{self.__class__.__name__}'
        sender = f'sender={self.sender}'
        receiver = f'receiver={self.receiver}'
        kind = f'kind={self.kind}'
        data = f'data={self.data}'
        sequence = f'{self.previous_id} -> {self.id}'
        return f'{cls}({sender}, {receiver}, {kind}, {data}) {sequence}'
