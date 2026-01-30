from nikon_ti2 import NikonTi2Adapter

adapter = NikonTi2Adapter(unload_before_init=True)

stage, pfs = adapter.initialize(stage_config=None)  # pass your StageConfig if you have one

# Stage (mm units)
print("move x")
stage.move_x(1.0)  # +1.0 mm
print("move y")
stage.move_y_to(5.0)  # y = 5.0 mm
pos = stage.get_pos()
print(pos)


# PFS (µm offset)
pfs.set_pfs_state(True)
print("pfs on")
pfs.set_offset(50.0)  # 50 µm
print("offset set")
pfs.wait_until_locked(timeout_s=2.0, allow_when_off=False)
