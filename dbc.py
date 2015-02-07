import struct

class Mapping:
    def __init__(self, r, t, i):
        self.index = r
        self.type = t
        self.identifier = i

class DbcEntry:
    pass

class Dbc:
    def __init__(self, filename, mappings, type=DbcEntry):
        """DBC file is assumed to be little-endian encoded"""
        f = open(filename, 'rb')
        self.type = type
        self.mappings = mappings
        try:
            self._parse(f)
        finally:
            f.close()

    def _parse(self, f):
        if (f.read(1) != b'W' or f.read(1) != b'D' or f.read(1) != b'B'  or
            f.read(1) != b'C'):
            raise RuntimeError
        rows = struct.unpack('<I', f.read(4))[0]
        cols = struct.unpack('<I', f.read(4))[0]
        row_size = struct.unpack('<I', f.read(4))[0]
        string_size = struct.unpack('<I', f.read(4))[0]

        if row_size / 4 != cols:
            raise RuntimeError

        # Read table as binary blob
        bin_blob = [None] * rows
        for i in range(0, rows):
            bin_blob[i] = f.read(row_size)

        # Read string table
        string_table = f.read(string_size)

        # Create table from provided mapping
        self.table = [None] * rows
        for i in range(0, rows):
            self.table[i] = self._map_single(bin_blob[i], string_table)

    def _map_single(self, raw, string_table):
        entry = self.type()
        for mapping in self.mappings:
            if mapping.type == str:
                index = struct.unpack_from('<I', raw, mapping.index * 4)[0]
                bstr = []
                while True:
                    if string_table[index] == 0:
                        break
                    bstr.append(string_table[index])
                    index += 1
                # TODO: Are strings actually utf-8 encoded?
                s = bytes(bstr).decode('utf-8')
                setattr(entry, mapping.identifier, s)
            elif mapping.type == int:
                v = struct.unpack_from('<I', raw, mapping.index * 4)[0]
                setattr(entry, mapping.identifier, v)
            elif mapping.type == float:
                v = struct.unpack_from('<I', raw, mapping.index * 4)[0]
                setattr(entry, mapping.identifier, v)
            else:
                raise RuntimeError
        return entry