#!/usr/bin/env python3
"""Unit tests for ball_detector postprocessing (pure numpy, no cv2/onnxruntime)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import numpy as np

from ball_detector import postprocess


def make_output(boxes, class_scores):
    """boxes: list of (cx, cy, w, h); class_scores: list of lists (per class, 0..1)."""
    anchors = len(boxes)
    num_classes = len(class_scores[0])
    out = np.zeros((1, 4 + num_classes, anchors), dtype=np.float32)
    for i, (cx, cy, w, h) in enumerate(boxes):
        out[0, 0, i] = cx
        out[0, 1, i] = cy
        out[0, 2, i] = w
        out[0, 3, i] = h
    for i, scores in enumerate(class_scores):
        for c, prob in enumerate(scores):
            out[0, 4 + c, i] = prob
    return out


class TestPostprocess(unittest.TestCase):
    def setUp(self):
        # 640x360 source letterboxed into a 416x416 canvas:
        # scale = 416/640 = 0.65, pad = ((416 - 360*0.65)/2) = (0, 91)
        self.img_shape = (360, 640, 3)
        self.scale = 0.65
        self.pad = (0, 91)

    def test_single_detection_center_and_scale(self):
        # canvas-space box centered at (208, 208) maps back to (320, 180)
        cx_c, cy_c, w_c, h_c = 208.0, 208.0, 80.0, 60.0
        raw_score = 0.9
        out = make_output([(cx_c, cy_c, w_c, h_c)], [[raw_score, 0.1, 0.1]])
        dets = postprocess(out, 0.25, 0.45, self.img_shape, self.scale, self.pad)
        self.assertEqual(len(dets), 1)
        d = dets[0]
        expected_cx = (cx_c - self.pad[0]) / self.scale
        expected_cy = (cy_c - self.pad[1]) / self.scale
        self.assertAlmostEqual(d["cx"], expected_cx, places=1)
        self.assertAlmostEqual(d["cy"], expected_cy, places=1)
        self.assertAlmostEqual(d["w"], w_c / self.scale, places=1)
        self.assertAlmostEqual(d["h"], h_c / self.scale, places=1)
        self.assertEqual(d["cls"], 0)
        self.assertAlmostEqual(d["conf"], raw_score, places=5)

    def test_confidence_threshold_filters_low_scores(self):
        out = make_output(
            [(100, 100, 50, 50), (300, 300, 50, 50)],
            [[0.9, 0.1, 0.1], [0.05, 0.1, 0.1]],
        )
        dets = postprocess(out, 0.25, 0.45, self.img_shape, self.scale, self.pad)
        self.assertEqual(len(dets), 1)
        self.assertEqual(dets[0]["cls"], 0)

    def test_class_selection(self):
        out = make_output(
            [(100, 100, 50, 50), (300, 300, 50, 50), (400, 150, 50, 50)],
            [
                [0.1, 0.9, 0.1],
                [0.1, 0.1, 0.9],
                [0.9, 0.1, 0.1],
            ],
        )
        dets = postprocess(out, 0.25, 0.45, self.img_shape, self.scale, self.pad)
        classes = sorted(d["cls"] for d in dets)
        self.assertEqual(classes, [0, 1, 2])

    def test_iou_suppresses_overlapping_boxes(self):
        out = make_output(
            [(200, 200, 100, 100), (210, 210, 100, 100)],
            [[0.9, 0.1, 0.1], [0.9, 0.1, 0.1]],
        )
        dets = postprocess(out, 0.25, 0.45, self.img_shape, self.scale, self.pad)
        self.assertEqual(len(dets), 1)

    def test_no_detections_below_threshold(self):
        out = make_output([(200, 200, 50, 50)], [[0.05, 0.05, 0.05]])
        dets = postprocess(out, 0.25, 0.45, self.img_shape, self.scale, self.pad)
        self.assertEqual(len(dets), 0)


if __name__ == "__main__":
    unittest.main()
