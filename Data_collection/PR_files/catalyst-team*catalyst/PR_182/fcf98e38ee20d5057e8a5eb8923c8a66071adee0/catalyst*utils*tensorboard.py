import struct
from collections import namedtuple
from collections.abc import Iterable
from crc32c import crc32 as crc32c
from pathlib import Path
from typing import BinaryIO, Union, Optional

import cv2
import numpy as np
from tensorboard.compat.proto.event_pb2 import Event


def _u32(x):
    return x & 0xffffffff


def _masked_crc32c(data):
    x = _u32(crc32c(data))
    return _u32(((x >> 15) | _u32(x << 17)) + 0xa282ead8)


class EventReadingError(Exception):
    """
    An exception that correspond to an event file reading error
    """
    pass


class EventsFileReader(Iterable):
    """
    An iterator over a Tensorboard events file
    """

    def __init__(self, events_file: BinaryIO):
        """
        Initialize an iterator over an events file

        :param events_file: An opened file-like object.
        """
        self._events_file = events_file

    def _read(self, size: int) -> Optional[bytes]:
        """
        Read exactly next `size` bytes from the current stream.

        :param size: A size in bytes to be read.
        :return: A `bytes` object with read data or `None` on EOF.
        :except: NotImplementedError if the stream is in non-blocking mode.
        :except: EventReadingError on reading error.
        """
        data = self._events_file.read(size)
        if data is None:
            raise NotImplementedError(
                'Reading of a stream in non-blocking mode'
            )
        if 0 < len(data) < size:
            raise EventReadingError(
                'The size of read data is less than requested size'
            )
        if len(data) == 0:
            return None
        return data

    def _read_and_check(self, size: int) -> Optional[bytes]:
        """
        Read and check data described by a format string.

        :param size: A size in bytes to be read.
        :return: A decoded number.
        :except: NotImplementedError if the stream is in non-blocking mode.
        :except: EventReadingError on reading error.
        """
        data = self._read(size)
        if data is None:
            return None
        checksum_size = struct.calcsize('I')
        checksum = struct.unpack('I', self._read(checksum_size))[0]
        checksum_computed = _masked_crc32c(data)
        if checksum != checksum_computed:
            raise EventReadingError(
                'Invalid checksum. {checksum} != {crc32}'.format(
                    checksum=checksum, crc32=checksum_computed
                )
            )
        return data

    def __iter__(self) -> Event:
        """
        Iterates over events in the current events file

        :return: An Event object
        :except: NotImplementedError if the stream is in non-blocking mode.
        :except: EventReadingError on reading error.
        """
        while True:
            header_size = struct.calcsize('Q')
            header = self._read_and_check(header_size)
            if header is None:
                break
            event_size = struct.unpack('Q', header)[0]
            event_raw = self._read_and_check(event_size)
            if event_raw is None:
                raise EventReadingError('Unexpected end of events file')
            event = Event()
            event.ParseFromString(event_raw)
            yield event


SummaryItem = namedtuple('SummaryItem', ['tag', 'step', 'wall_time', 'value', 'type'])


class SummaryReader(Iterable):
    """
    Iterates over events in all the files in the current logdir.
    Only scalars and images are supported at the moment.
    """

    def __init__(
        self, logdir: Union[str, Path],
        tag_filter: Optional[Iterable] = None,
        type_filter: Optional[Iterable] = None
    ):
        """
        Initalize new summary reader
        :param logdir: A directory with Tensorboard summary data
        :param tag_filter: A list of tags to leave (`None` for all)
        :param type_filter: A list of types to leave (`None` for all)
            Note that only 'scalar' and 'image' types are allowed at the moment.
        """
        self._logdir = Path(logdir)
        self._tag_filter = set(tag_filter) if tag_filter is not None else None
        self._type_filter = set(type_filter) if type_filter is not None else None

    @staticmethod
    def _decode_image(encoded_image) -> np.ndarray:
        """
        Decode binary image representation to Numpy array
        :param encoded_image: An encoded image data
        :return: A Numpy array with an HÃWÃC image
        """
        buf = np.frombuffer(encoded_image, np.uint8)
        data = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        return data

    @classmethod
    def _decode_events(cls, events: Iterable) -> Optional[SummaryItem]:
        """
        Convert events to `SummaryItem` instances
        :param events: An iterable with events objects
        :return: A generator with decoded events
            or `None`s if an event can't be decoded
        """
        for event in events:
            if not event.HasField('summary'):
                yield None
            step = event.step
            wall_time = event.wall_time
            for value in event.summary.value:
                tag = value.tag
                if value.HasField('simple_value'):
                    data = value.simple_value
                    event_type = 'scalar'
                elif value.HasField('image'):
                    data = cls._decode_image(value.image.encoded_image_string)
                    event_type = 'image'
                else:
                    yield None
                    continue
                yield SummaryItem(
                    tag=tag, step=step, wall_time=wall_time,
                    value=data, type=event_type
                )

    def _check_tag(self, tag: str) -> bool:
        """
        Check if a tag matches the current tag filter
        :param tag: A string with tag
        :return: A boolean value.
        """
        return self._tag_filter is None or tag in self._tag_filter

    def _check_type(self, event_type: str) -> bool:
        """
        Check if a tag matches the current tag filter
        :param event_type: A string with type name
        :return: A boolean value.
        """
        return self._type_filter is None or event_type in self._type_filter

    def __iter__(self) -> SummaryItem:
        """
        Iterate over events in all the files in the current logdir
        :return: A generator with `SummaryItem` objects
        """
        log_files = sorted(f for f in self._logdir.glob('*') if f.is_file())
        for file_path in log_files:
            with open(file_path, 'rb') as f:
                reader = EventsFileReader(f)
                yield from (
                    item for item in self._decode_events(reader)
                    if item is not None
                       and self._check_tag(item.tag)
                       and self._check_type(item.type)
                )
