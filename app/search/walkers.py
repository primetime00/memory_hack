import ctypes

from mem_edit import Process


class EntireWalker():
    def __init__(self, memory: Process, value_type):
        self.memory = memory
        self.value_type = value_type
        self.num = 0
        self.regions = list(memory.list_mapped_regions(True))
        self.regionIndex = 0
        self.byteIndex = 0
        self.size = 0
        self.count = 0
        self.current_region = self.read_region()

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def read_region(self):
        while True:
            start = self.regions[self.regionIndex][0]
            end = self.regions[self.regionIndex][1]
            self.size = end - start
            region_buffer = (ctypes.c_byte * self.size)()
            try:
                self.memory.read_memory(start, region_buffer)
            except OSError:
                self.regionIndex += 1
                self.count += self.size
                continue
            break
        return region_buffer

    def _get_count(self):
        r = self.count
        self.count = 0
        return r

    def eof(self):
        return self.regionIndex >= len(self.regions)

    def increment(self):
        self.byteIndex += 1
        self.count += 1
        if self.byteIndex >= self.size - (ctypes.sizeof(self.value_type) - 1):
            self.regionIndex += 1
            self.byteIndex = 0
            self.count = 0
            if self.regionIndex < len(self.regions):
                self.current_region = self.read_region()

    def next(self):
        if self.eof():
            raise StopIteration()
        while True:
            region = self.regions[self.regionIndex]
            read = self.value_type.__class__.from_buffer(self.current_region, self.byteIndex)
            result = read, region[0] + self.byteIndex, self._get_count() + 1
            self.increment()
            break
        return result


class RegionWalker():
    def __init__(self, memory:Process, value_type: ctypes._SimpleCData, start, stop):
        self.memory = memory
        self.value_type = value_type
        self.start = start
        self.stop = stop
        self.size = stop - start
        self.byteIndex = 0
        self.current_region = self.read_region()

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def read_region(self):
        try:
            region_buffer = (ctypes.c_byte * self.size)()
            self.memory.read_memory(self.start, region_buffer)
            return region_buffer
        except OSError:
            return None

    def eof(self):
        return self.current_region is None or self.byteIndex >= self.size

    def increment(self):
        self.byteIndex += ctypes.sizeof(self.value_type)

    def next(self):
        if self.eof():
            raise StopIteration()
        while True:
            read = self.value_type.from_buffer(self.current_region, self.byteIndex)
            result = read, self.start + self.byteIndex
            self.increment()
            break
        return result


class NormalizedWalker():
    def __init__(self, memory:Process, value_type: ctypes._SimpleCData, region_data):
        self.memory = memory
        self.value_type = value_type

        self.byteIndex = 0
        self.regionIndex = 0

        self.region_list = self.read_region(region_data)
        self.current_size = len(self.region_list[0]['data'])
        self.end = self.current_size - (ctypes.sizeof(self.value_type) - 1)

    def __len__(self):
        return sum([len(self.region_list[x]['data']) for x in range(0, len(self.region_list))])

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def read_region(self, segments):
        buffers = []
        for segment in segments:
            try:
                region_buffer = (ctypes.c_byte * (segment['stop'] - segment['start']))()
                self.memory.read_memory(segment['start'], region_buffer)
                buffers.append({'start': segment['start'], 'data': region_buffer})
            except OSError:
                continue
        return buffers

    def eof(self):
        return not self.region_list or self.regionIndex >= len(self.region_list)

    def increment(self):
        self.byteIndex += ctypes.sizeof(self.value_type)
        if self.byteIndex >= self.end:
            self.regionIndex += 1
            self.byteIndex = 0
            if self.regionIndex < len(self.region_list):
                self.current_size = len(self.region_list[self.regionIndex]['data'])
                self.end = self.current_size - (ctypes.sizeof(self.value_type) - 1)

    def next(self):
        if self.eof():
            raise StopIteration()
        while True:
            read = self.value_type.from_buffer(self.region_list[self.regionIndex]['data'], self.byteIndex)
            result = read, self.region_list[self.regionIndex]['start'] + self.byteIndex
            self.increment()
            break
        return result

class BufferWalker():
    def __init__(self, buffer):
        self.buffer = buffer
        self.byteIndex = 0

    def __len__(self):
        return len(self.buffer)

    def __iter__(self):
        return self

    def __next__(self):
        return self.next()

    def eof(self):
        return self.byteIndex >= len(self.buffer) - (self.buffer.store_size - 1)

    def increment(self):
        self.byteIndex += self.buffer.get_store_size()

    def next(self):
        if self.eof():
            raise StopIteration()
        read_value = self.buffer.read(self.byteIndex)
        result = read_value, self.buffer.get_start_offset() + self.byteIndex
        self.increment()
        return result
