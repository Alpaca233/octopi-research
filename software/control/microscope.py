import serial
import time
import os
import sys
import math
import re
import numpy as np
import imageio as iio

from PyQt5.QtCore import QObject

import software.control.core as core
from software.control._def import *
import software.control

if CAMERA_TYPE == "Toupcam":
    import software.control.camera_toupcam as camera
import software.control.microcontroller as microcontroller
import software.control.serial_peripherals as serial_peripherals


class Microscope(QObject):

    def __init__(self, microscope=None, is_simulation=True):
        super().__init__()
        if microscope is None:
            self.initialize_camera(is_simulation=is_simulation)
            self.initialize_microcontroller(is_simulation=is_simulation)
            self.initialize_core_components()
            self.initialize_peripherals()
        else:
            self.camera = microscope.camera
            self.microcontroller = microscope.microcontroller
            self.configurationManager = microscope.microcontroller
            self.objectiveStore = microscope.objectiveStore
            self.streamHandler = microscope.streamHandler
            self.liveController = microscope.liveController
            self.navigationController = microscope.navigationController
            self.autofocusController = microscope.autofocusController
            self.slidePositionController = microscope.slidePositionController
            if USE_ZABER_EMISSION_FILTER_WHEEL:
                self.emission_filter_wheel = microscope.emission_filter_wheel
            elif USE_OPTOSPIN_EMISSION_FILTER_WHEEL:
                self.emission_filter_wheel = microscope.emission_filter_wheel

    def initialize_camera(self, is_simulation):
        if is_simulation:
            self.camera = camera.Camera_Simulation(rotate_image_angle=ROTATE_IMAGE_ANGLE, flip_image=FLIP_IMAGE)
        else:
            sn_camera_main = camera.get_sn_by_model(MAIN_CAMERA_MODEL)
            self.camera = camera.Camera(sn=sn_camera_main, rotate_image_angle=ROTATE_IMAGE_ANGLE, flip_image=FLIP_IMAGE)
        
        self.camera.open()
        self.camera.set_pixel_format(DEFAULT_PIXEL_FORMAT)
        self.camera.set_software_triggered_acquisition()

    def initialize_microcontroller(self, is_simulation):
        if is_simulation:
            self.microcontroller = microcontroller.Microcontroller(existing_serial=software.control.microcontroller.SimSerial())
        else:
            self.microcontroller = microcontroller.Microcontroller(version=CONTROLLER_VERSION, sn=CONTROLLER_SN)
        
        self.microcontroller.reset()
        time.sleep(0.5)
        self.microcontroller.initialize_drivers()
        time.sleep(0.5)
        self.microcontroller.configure_actuators()

        self.home_x_and_y_separately = False

    def initialize_core_components(self):
        self.configurationManager = core.ConfigurationManager(filename='./channel_configurations.xml')
        self.objectiveStore = core.ObjectiveStore()
        self.streamHandler = core.StreamHandler(display_resolution_scaling=DEFAULT_DISPLAY_CROP/100)
        self.liveController = core.LiveController(self.camera, self.microcontroller, self.configurationManager, self)
        self.navigationController = core.NavigationController(self.microcontroller, self.objectiveStore)
        self.autofocusController = core.AutoFocusController(self.camera, self.navigationController, self.liveController)
        self.slidePositionController = core.SlidePositionController(self.navigationController,self.liveController)

    def initialize_peripherals(self):
        if USE_ZABER_EMISSION_FILTER_WHEEL:
            self.emission_filter_wheel = serial_peripherals.FilterController(FILTER_CONTROLLER_SERIAL_NUMBER, 115200, 8, serial.PARITY_NONE, serial.STOPBITS_ONE)
            self.emission_filter_wheel.start_homing()
        elif USE_OPTOSPIN_EMISSION_FILTER_WHEEL:
            self.emission_filter_wheel = serial_peripherals.Optospin(SN=FILTER_CONTROLLER_SERIAL_NUMBER)
            self.emission_filter_wheel.set_speed(OPTOSPIN_EMISSION_FILTER_WHEEL_SPEED_HZ)

    def set_channel(self,channel):
        self.liveController.set_channel(channel)

    def acquire_image(self):
        # turn on illumination and send trigger
        if self.liveController.trigger_mode == TriggerMode.SOFTWARE:
            self.liveController.turn_on_illumination()
            self.waitForMicrocontroller()
            self.camera.send_trigger()
        elif self.liveController.trigger_mode == TriggerMode.HARDWARE:
            self.microcontroller.send_hardware_trigger(control_illumination=True,illumination_on_time_us=self.camera.exposure_time*1000)
        
        # read a frame from camera
        image = self.camera.read_frame()
        if image is None:
            print('self.camera.read_frame() returned None')
        
        # tunr off the illumination if using software trigger
        if self.liveController.trigger_mode == TriggerMode.SOFTWARE:
            self.liveController.turn_off_illumination()
        
        return image

    def to_loading_position(self):
        # retract z
        timestamp_start = time.time()
        self.slidePositionController.z_pos = self.navigationController.z_pos # zpos at the beginning of the scan
        self.navigationController.move_z_to(OBJECTIVE_RETRACTED_POS_MM)
        self.waitForMicrocontroller()
        print('z retracted')
        self.slidePositionController.objective_retracted = True

        # for wellplates
        # reset limits
        self.navigationController.set_x_limit_pos_mm(100)
        self.navigationController.set_x_limit_neg_mm(-100)
        self.navigationController.set_y_limit_pos_mm(100)
        self.navigationController.set_y_limit_neg_mm(-100)
        # home for the first time
        if self.slidePositionController.homing_done == False:
            print('running homing first')
            timestamp_start = time.time()
            # x needs to be at > + 20 mm when homing y
            self.navigationController.move_x(20)
            self.waitForMicrocontroller()
            # home y
            self.navigationController.home_y()
            self.waitForMicrocontroller()
            self.navigationController.zero_y()
            # home x
            self.navigationController.home_x()
            self.waitForMicrocontroller()
            self.navigationController.zero_x()
            self.slidePositionController.homing_done = True
        # homing done previously
        else:
            timestamp_start = time.time()
            self.navigationController.move_x_to(20)
            self.waitForMicrocontroller()
            self.navigationController.move_y_to(SLIDE_POSITION.LOADING_Y_MM)
            self.waitForMicrocontroller()
            self.navigationController.move_x_to(SLIDE_POSITION.LOADING_X_MM)
            self.waitForMicrocontroller()
        # set limits again
        self.navigationController.set_x_limit_pos_mm(SOFTWARE_POS_LIMIT.X_POSITIVE)
        self.navigationController.set_x_limit_neg_mm(SOFTWARE_POS_LIMIT.X_NEGATIVE)
        self.navigationController.set_y_limit_pos_mm(SOFTWARE_POS_LIMIT.Y_POSITIVE)
        self.navigationController.set_y_limit_neg_mm(SOFTWARE_POS_LIMIT.Y_NEGATIVE)

    def perform_scanning(self, path, z_pos_um, xy_coordinates_mm, fov_ids):
        self.liveController.set_microscope_mode(self.configurationManager.configurations[0])
        self.navigationController.move_z_to(z_pos_um / 1000)

        os.makedirs(os.path.abspath(path), exist_ok=True)

        for i in range(len(xy_coordinates_mm)):
            self.navigationController.move_x_to(xy_coordinates_mm[i][0])
            self.navigationController.move_y_to(xy_coordinates_mm[i][1])
            self.waitForMicrocontroller()
            image = self.acquire_image()
            filename = os.path.join(path, str(i) + '_' + fov_ids[i] + '.tiff')
            self.save_image(filename, image)

    def save_image(self, saving_path, image):
        iio.imwrite(saving_path, image)

    def get_scan_coordinates_from_selected_wells(self, wellplate_format, selected, scan_size_mm=None, overlap_percent=10):
        wellplate_settings = self.get_wellplate_settings(wellplate_format)
        center_coordinates, well_names = self.get_selected_well_coordinates(selected, wellplate_settings)

        if wellplate_format == '384 well plate' or '1536 well plate':
            well_shape = 'Square'
        else:
            well_shape = 'Circle'

        scan_coordinates = []
        names = []

        if scan_size_mm is None:
            scan_size_mm = wellplate_settings['well_size_mm']

        for (x, y), n in zip(center_coordinates, well_names):
            coords = self.create_region_coordinates(x, y, scan_size_mm, overlap_percent, well_shape)
            scan_coordinates.extend(coords)
            names.extend(n * len(coords))

        return scan_coordinates, names

    def get_selected_well_coordinates(self, selected, wellplate_settings):
        pattern = r'([A-Za-z]+)(\d+):?([A-Za-z]*)(\d*)'
        descriptions = selected.split(',')
        coordinates_mm = []
        names = []
        for desc in descriptions:
            match = re.match(pattern, desc.strip())
            if match:
                start_row, start_col, end_row, end_col = match.groups()
                start_row_index = self._row_to_index(start_row)
                start_col_index = int(start_col) - 1

                if end_row and end_col:  # It's a range
                    end_row_index = self._row_to_index(end_row)
                    end_col_index = int(end_col) - 1
                    for row in range(min(start_row_index, end_row_index), max(start_row_index, end_row_index) + 1):
                        cols = range(min(start_col_index, end_col_index), max(start_col_index, end_col_index) + 1)
                        # Reverse column order for alternating rows if needed
                        if (row - start_row_index) % 2 == 1:
                            cols = reversed(cols)

                        for col in cols:
                            x_mm = wellplate_settings['a1_x_mm'] + col*wellplate_settings['well_spacing_mm'] + WELLPLATE_OFFSET_X_mm
                            y_mm = wellplate_settings['a1_y_mm'] + row*wellplate_settings['well_spacing_mm'] + WELLPLATE_OFFSET_Y_mm
                            coordinates_mm.append((x_mm, y_mm))
                            names.append(self._index_to_row(row) + str(col+1))
                else: 
                    x_mm = wellplate_settings['a1_x_mm'] + start_col_index*wellplate_settings['well_spacing_mm'] + WELLPLATE_OFFSET_X_mm
                    y_mm = wellplate_settings['a1_y_mm'] + start_row_index*wellplate_settings['well_spacing_mm'] + WELLPLATE_OFFSET_Y_mm
                    coordinates_mm.append((x_mm, y_mm))
                    names.append(start_row + start_col)

        return coordinates_mm, names

    def _row_to_index(self, row):
        index = 0
        for char in row:
            index = index * 26 + (ord(char.upper()) - ord('A') + 1)
        return index - 1

    def _index_to_row(self,index):
        index += 1
        row = ""
        while index > 0:
            index -= 1
            row = chr(index % 26 + ord('A')) + row
            index //= 26
        return row

    def get_wellplate_settings(self, wellplate_format):
        if wellplate_format in WELLPLATE_FORMAT_SETTINGS:
            settings = WELLPLATE_FORMAT_SETTINGS[wellplate_format]
        elif wellplate_format == '0':
            settings = {
                'format': '0',
                'a1_x_mm': 0,
                'a1_y_mm': 0,
                'a1_x_pixel': 0,
                'a1_y_pixel': 0,
                'well_size_mm': 0,
                'well_spacing_mm': 0,
                'number_of_skip': 0,
                'rows': 1,
                'cols': 1
            }
        else:
            return None
        return settings

    def create_region_coordinates(self, center_x, center_y, scan_size_mm, overlap_percent=10, shape='Square'):
        #if shape == 'Manual':
        #    return self.create_manual_region_coordinates(objectiveStore, self.manual_shapes, overlap_percent)

        #if scan_size_mm is None:
        #    scan_size_mm = self.wellplate_settings.well_size_mm
        pixel_size_um = self.objectiveStore.get_pixel_size()
        fov_size_mm = (pixel_size_um / 1000) * Acquisition.CROP_WIDTH
        step_size_mm = fov_size_mm * (1 - overlap_percent / 100)

        steps = math.floor(scan_size_mm / step_size_mm)
        if shape == 'Circle':
            tile_diagonal = math.sqrt(2) * fov_size_mm
            if steps % 2 == 1:  # for odd steps
                actual_scan_size_mm = (steps - 1) * step_size_mm + tile_diagonal
            else:  # for even steps
                actual_scan_size_mm = math.sqrt(((steps - 1) * step_size_mm + fov_size_mm)**2 + (step_size_mm + fov_size_mm)**2)

            if actual_scan_size_mm > scan_size_mm:
                actual_scan_size_mm -= step_size_mm
                steps -= 1
        else:
            actual_scan_size_mm = (steps - 1) * step_size_mm + fov_size_mm

        steps = max(1, steps)  # Ensure at least one step
        # print(f"steps: {steps}, step_size_mm: {step_size_mm}")
        # print(f"scan size mm: {scan_size_mm}")
        # print(f"actual scan size mm: {actual_scan_size_mm}")

        scan_coordinates = []
        half_steps = (steps - 1) / 2
        radius_squared = (scan_size_mm / 2) ** 2
        fov_size_mm_half = fov_size_mm / 2

        for i in range(steps):
            row = []
            y = center_y + (i - half_steps) * step_size_mm
            for j in range(steps):
                x = center_x + (j - half_steps) * step_size_mm
                if shape == 'Square' or (shape == 'Circle' and self._is_in_circle(x, y, center_x, center_y, radius_squared, fov_size_mm_half)):
                    row.append((x, y))
                    #self.navigationViewer.register_fov_to_image(x, y)

            if FOV_PATTERN == 'S-Pattern' and i % 2 == 1:
                row.reverse()
            scan_coordinates.extend(row)

        if not scan_coordinates and shape == 'Circle':
            scan_coordinates.append((center_x, center_y))
            #self.navigationViewer.register_fov_to_image(center_x, center_y)

        #self.signal_update_navigation_viewer.emit()
        return scan_coordinates

    def _is_in_circle(self, x, y, center_x, center_y, radius_squared, fov_size_mm_half):
        corners = [
            (x - fov_size_mm_half, y - fov_size_mm_half),
            (x + fov_size_mm_half, y - fov_size_mm_half),
            (x - fov_size_mm_half, y + fov_size_mm_half),
            (x + fov_size_mm_half, y + fov_size_mm_half)
        ]
        return all((cx - center_x)**2 + (cy - center_y)**2 <= radius_squared for cx, cy in corners)

    def home_xyz(self):
        if HOMING_ENABLED_Z:
            self.navigationController.home_z()
            self.waitForMicrocontroller(10, 'z homing timeout')
        if HOMING_ENABLED_X and HOMING_ENABLED_Y:
            self.navigationController.move_x(20)
            self.waitForMicrocontroller()
            self.navigationController.home_y()
            self.waitForMicrocontroller(10, 'y homing timeout')
            self.navigationController.zero_y()
            self.navigationController.home_x()
            self.waitForMicrocontroller(10, 'x homing timeout')
            self.navigationController.zero_x()
            self.slidePositionController.homing_done = True

    def move_x(self,distance,blocking=True):
        self.navigationController.move_x(distance)
        if blocking:
            self.waitForMicrocontroller()

    def move_y(self,distance,blocking=True):
        self.navigationController.move_y(distance)
        if blocking:
            self.waitForMicrocontroller()

    def move_x_to(self,position,blocking=True):
        self.navigationController.move_x_to(position)
        if blocking:
            self.waitForMicrocontroller()

    def move_y_to(self,position,blocking=True):
        self.navigationController.move_y_to(position)
        if blocking:
            self.waitForMicrocontroller()

    def get_x(self):
        return self.navigationController.x_pos_mm

    def get_y(self):
        return self.navigationController.y_pos_mm

    def get_z(self):
        return self.navigationController.z_pos_mm

    def move_z_to(self,z_mm,blocking=True):
        clear_backlash = True if (z_mm < self.navigationController.z_pos_mm and self.navigationController.get_pid_control_flag(2)==False) else False
        # clear backlash if moving backward in open loop mode
        self.navigationController.move_z_to(z_mm)
        if blocking:
            self.waitForMicrocontroller()
            if clear_backlash:
                _usteps_to_clear_backlash = 160
                self.navigationController.move_z_usteps(-_usteps_to_clear_backlash)
                self.waitForMicrocontroller()
                self.navigationController.move_z_usteps(_usteps_to_clear_backlash)
                self.waitForMicrocontroller()

    def start_live(self):
        self.camera.start_streaming()
        self.liveController.start_live()

    def stop_live(self):
        self.liveController.stop_live()
        self.camera.stop_streaming()

    def waitForMicrocontroller(self, timeout=5.0, error_message=None):
        try:
            self.microcontroller.wait_till_operation_is_completed(timeout)
        except TimeoutError as e:
            self.log.error(error_message or "Microcontroller operation timed out!")
            raise e

    def close(self):
        self.stop_live()
        self.camera.close()
        self.microcontroller.close()
        if USE_ZABER_EMISSION_FILTER_WHEEL or USE_OPTOSPIN_EMISSION_FILTER_WHEEL:
            self.emission_filter_wheel.close()
