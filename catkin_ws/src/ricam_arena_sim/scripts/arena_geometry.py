#!/usr/bin/env python3
"""Shared metric geometry for the RICAM arena assets."""

FIELD_WIDTH_M = 3.0
FIELD_HEIGHT_M = 2.5
WALL_THICKNESS_M = 0.05

# Recovered from the user's Blender edit-mode cube that had been merged into
# kt_label_2. The box sits flush on the floor beside the west wall.
SIDE_BOX_CENTER_M = (-1.273845, 0.068412, 0.145220)
SIDE_BOX_SIZE_M = (0.349632, 1.656391, 0.290440)

RECOGNITION_ZONE_SIZE_X_M = 0.80
RECOGNITION_ZONE_SIZE_Y_M = 0.50
RECOGNITION_ZONE_GAP_M = 0.30
RECOGNITION_BOX_SIZE_M = 0.30

DELIVERY_TARGETS = (
    (-0.901751, 0.760000),
    (-0.595191, 0.758326),
    (-0.290919, 0.758987),
    (0.018237, 0.758961),
)

PICKUP_ZONE_CENTER_X_M = -0.407637
PICKUP_ZONE_CENTER_Y_M = -0.40
PICKUP_BALL_X_M = (-0.632245, -0.482520, -0.346039, -0.205378)

RECOGNITION_ZONES = (
    (0.728636, 0.40, "A", "APPLE"),
    (0.722738, -0.40, "B", "CLOTHES"),
)

# Horizontal positions follow the user's Blender layout. Both boxes are restored
# to their row centre and to z=0.15 m by the Blender generator.
RECOGNITION_BOXES = ((0.694172, 0.40), (0.954366, -0.40))
