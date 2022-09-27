import ctypes

from app.script_common import BaseScript
from app.script_common.aob import AOB
from app.script_ui import Toggle, InputButton, BaseUI


class Test(BaseScript):
    resources_aob = AOB('Resources', "70 F3 28 00 60 F6 28 00 10 F6 28 00 F0 F2 28 00 00 00 00 00 00 00 00 00 4D 17 00 00 C8 00 00 00 00 00 00")
    pointer_aob = AOB('Pointer', "3F 66 66 26 3F 14 AE 47 3F 9A 99 59 3F 33 33 73 3F 0A D7 83 3F 71 3D 8A 3F 29 5C 8F 3F 33 33 93 3F 3D 0A")

    resource_offsets = [
        {'offset': 0x6d1b, 'value': ctypes.c_uint16(65500)},
        {'offset': 0x6d1f, 'value': ctypes.c_uint16(65500)},
        {'offset': 0x6d23, 'value': ctypes.c_uint16(65500)},
        {'offset': 0x6d27, 'value': ctypes.c_uint16(65500)},
        {'offset': 0x6d2b, 'value': ctypes.c_uint16(65500)},
        {'offset': 0x6d2f, 'value': ctypes.c_uint16(65500)},
        {'offset': 0x6d33, 'value': ctypes.c_uint16(65500)},
    ]
    pointer_offset = 0xEF6D
    army_magic = 0x2ED6CE
    movement_magic = 0x2ED703

    def on_load(self):
        self.add_aob(self.resources_aob)
        self.add_aob(self.pointer_aob)

    def get_name(self):
        return "Test Script"

    def get_app(self):
        return ['retroarch', 'retroarch.exe', 'dosbox.exe']

    def build_ui(self):
        self.add_ui_element(Toggle("Unlimited Resources", self.unlimited_resources, self.is_resource_found))
        self.add_ui_element(InputButton("Set Army # of Selected", self.add_army, self.is_pointer_found, default_value="100", validation_checker=self.limit_value))
        self.add_ui_element(Toggle("Unlimited Movement for Selected", self.unlimited_movement, self.is_pointer_found))

    def is_resource_found(self):
        return self.resources_aob.is_found()

    def is_pointer_found(self):
        return self.pointer_aob.is_found()

    def limit_value(self, val: str):
        try:
            val = int(val)
            if 0 < val < 1000:
                return val
            return None
        except ValueError:
            return None

    def add_army(self, control: BaseUI):
        val = control.input_handler.get_validated_value()
        pointer_value = self.get_memory().read_memory(self.pointer_aob.get_bases()[0] + self.pointer_offset, ctypes.c_uint32())
        starting_address = (self.pointer_aob.get_bases()[0] + self.pointer_offset) + pointer_value.value - self.army_magic
        number = self.get_memory().read_memory(starting_address, ctypes.c_uint16())
        for i in range(0, 5):
            addr = starting_address + (i*2)
            number = self.get_memory().read_memory(starting_address, ctypes.c_uint16())
            if number.value == 0:
                continue
            self.get_memory().write_memory(addr, ctypes.c_uint16(val))

    def unlimited_movement(self, control: BaseUI):
        pointer_value = self.get_memory().read_memory(self.pointer_aob.get_bases()[0] + self.pointer_offset, ctypes.c_uint32())
        if pointer_value.value > 0:
            addr = (self.pointer_aob.get_bases()[0] + self.pointer_offset) + pointer_value.value - self.movement_magic
            self.get_memory().write_memory(addr, ctypes.c_uint16(1000))


    def unlimited_resources(self, control: BaseUI):
        for offset in [x['offset'] for x in self.resource_offsets]:
            self.get_memory().write_memory(self.resources_aob.get_bases()[0] + offset, ctypes.c_int32(50000))



