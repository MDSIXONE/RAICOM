#!/usr/bin/env python3
"""Real-time ball detection (red/blue/green) from an MJPEG stream using a YOLOv8 ONNX model."""

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np


def letterbox(img, new_size, color=(114, 114, 114)):
    h, w = img.shape[:2]
    new_w, new_h = new_size
    scale = min(new_w / w, new_h / h)
    resized_w, resized_h = int(round(w * scale)), int(round(h * scale))
    resized = cv2.resize(img, (resized_w, resized_h), interpolation=cv2.INTER_LINEAR)
    canvas = np.full((new_h, new_w, 3), color, dtype=np.uint8)
    pad_x = (new_w - resized_w) // 2
    pad_y = (new_h - resized_h) // 2
    canvas[pad_y : pad_y + resized_h, pad_x : pad_x + resized_w] = resized
    return canvas, scale, pad_x, pad_y


def postprocess(output, conf_thres, iou_thres, img_shape, letterbox_scale, letterbox_pad):
    """Convert a raw YOLOv8 ONNX output tensor into per-class detections.

    output shape: [1, 4 + num_classes, num_anchors] (cx, cy, w, h in letterboxed pixels).
    Returns list of dicts: {cls, name, x1, y1, x2, y2, cx, cy, w, h, conf}.
    """
    orig_h, orig_w = img_shape[:2]
    scale, pad_x, pad_y = letterbox_scale, letterbox_pad[0], letterbox_pad[1]

    preds = output[0].T  # [num_anchors, 4 + num_classes]
    num_classes = preds.shape[1] - 4
    if num_classes < 1:
        raise ValueError("model output has no class scores")

    boxes_xywh = preds[:, :4]
    # YOLOv8 ONNX exports already apply sigmoid to class scores: raw 0..1.
    class_scores = preds[:, 4:]

    detections = []
    for c in range(num_classes):
        scores = class_scores[:, c]
        keep = np.where(scores >= conf_thres)[0]
        if keep.size == 0:
            continue
        cand_boxes = boxes_xywh[keep]
        cand_scores = scores[keep]
        xyxy = np.empty_like(cand_boxes)
        xyxy[:, 0] = cand_boxes[:, 0] - cand_boxes[:, 2] / 2.0
        xyxy[:, 1] = cand_boxes[:, 1] - cand_boxes[:, 3] / 2.0
        xyxy[:, 2] = cand_boxes[:, 0] + cand_boxes[:, 2] / 2.0
        xyxy[:, 3] = cand_boxes[:, 1] + cand_boxes[:, 3] / 2.0
        indices = cv2.dnn.NMSBoxes(
            xyxy.tolist(), cand_scores.tolist(), conf_thres, iou_thres
        )
        if isinstance(indices, tuple):
            indices = indices[0]
        if indices is None:
            continue
        for idx in np.asarray(indices).ravel():
            x1, y1, x2, y2 = xyxy[int(idx)]
            x1 = (x1 - pad_x) / scale
            y1 = (y1 - pad_y) / scale
            x2 = (x2 - pad_x) / scale
            y2 = (y2 - pad_y) / scale
            x1 = max(0.0, min(x1, orig_w - 1))
            y1 = max(0.0, min(y1, orig_h - 1))
            x2 = max(0.0, min(x2, orig_w - 1))
            y2 = max(0.0, min(y2, orig_h - 1))
            if x2 <= x1 or y2 <= y1:
                continue
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            detections.append(
                {
                    "cls": c,
                    "name": None,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "cx": cx,
                    "cy": cy,
                    "w": x2 - x1,
                    "h": y2 - y1,
                    "conf": float(cand_scores[int(idx)]),
                }
            )
    return detections


def load_session(model_path):
    try:
        import onnxruntime as ort
    except ImportError as exc:
        raise RuntimeError(
            "onnxruntime is required: pip install onnxruntime"
        ) from exc
    providers = ["CPUExecutionProvider"]
    session = ort.InferenceSession(str(model_path), providers=providers)
    return session


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Real-time red/blue/green ball detection from an MJPEG stream."
    )
    parser.add_argument("--model", required=True, help="path to YOLOv8 ONNX model")
    parser.add_argument(
        "--source",
        default="http://127.0.0.1:8090/stream.mjpg",
        help="video source: MJPEG URL or device index",
    )
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--iou", type=float, default=0.45)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument(
        "--names",
        default="red,blue,green",
        help="comma-separated class names matching model training order",
    )
    parser.add_argument(
        "--classes",
        nargs="+",
        type=int,
        default=None,
        help="only report these class indices (e.g. 0 2)",
    )
    parser.add_argument(
        "--max-frames",
        type=int,
        default=0,
        help="stop after N frames (0 = run forever)",
    )
    parser.add_argument(
        "--no-show",
        action="store_true",
        help="terminal only, do not open a cv2 window",
    )
    return parser.parse_args(argv)


def pick_color(name):
    lowered = name.lower()
    if "red" in lowered:
        return (0, 0, 255)
    if "blue" in lowered:
        return (255, 0, 0)
    if "green" in lowered:
        return (0, 255, 0)
    return (255, 255, 255)


def process_frame(frame, session, input_name, args, class_names, allowed_classes, frame_no):
    """Run inference on one frame; returns (inference_ms, detections)."""
    new_size = (args.imgsz, args.imgsz)
    boxed, scale, pad_x, pad_y = letterbox(frame, new_size)
    blob = cv2.dnn.blobFromImage(
        boxed, scalefactor=1.0 / 255.0, size=new_size, swapRB=True
    )

    start = time.perf_counter()
    outputs = session.run(None, {input_name: blob})
    infer_ms = (time.perf_counter() - start) * 1000.0

    detections = postprocess(
        outputs[0], args.conf, args.iou, frame.shape, scale, (pad_x, pad_y)
    )
    if allowed_classes is not None:
        detections = [d for d in detections if d["cls"] in allowed_classes]
    for d in detections:
        d["name"] = (
            class_names[d["cls"]] if d["cls"] < len(class_names) else f"cls{d['cls']}"
        )

    now = time.strftime("%H:%M:%S") + f".{int(time.time() * 1000) % 1000:03d}"
    if detections:
        print(f"[{now}] frame {frame_no}: {len(detections)} balls")
        for d in detections:
            print(
                f"  {d['name']:<8} center=({d['cx']:.0f},{d['cy']:.0f})  "
                f"size={d['w']:.0f}x{d['h']:.0f}  conf={d['conf']:.2f}"
            )
    return infer_ms, detections


def main():
    args = parse_args()
    model_path = Path(args.model)
    if not model_path.exists():
        print(f"ERROR: model file not found: {model_path}", file=sys.stderr)
        return 2

    class_names = [n.strip() for n in args.names.split(",") if n.strip()]
    if not class_names:
        print("ERROR: --names must contain at least one class", file=sys.stderr)
        return 2
    allowed_classes = set(args.classes) if args.classes else None

    session = load_session(model_path)
    input_name = session.get_inputs()[0].name
    expected_size = tuple(session.get_inputs()[0].shape[2:4])
    if args.imgsz not in expected_size:
        print(
            f"WARNING: model expects input {expected_size}, using --imgsz {args.imgsz}"
        )

    image_mode = Path(args.source).suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp")
    if image_mode:
        frame = cv2.imread(args.source)
        if frame is None:
            print(f"ERROR: cannot read image: {args.source}", file=sys.stderr)
            return 2
        infer_ms, _ = process_frame(
            frame, session, input_name, args, class_names, allowed_classes, 1
        )
        print(f"summary: single image, inference {infer_ms:.1f} ms")
        return 0

    cap = cv2.VideoCapture(args.source)
    if not cap.isOpened():
        print(f"ERROR: cannot open video source: {args.source}", file=sys.stderr)
        return 2

    show = not args.no_show
    if show:
        try:
            cv2.namedWindow("ball_detector")
        except cv2.error:
            show = False

    total_frames = 0
    det_frames = 0
    infer_times = []
    last_no_ball_log = 0.0
    try:
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                print("WARNING: failed to read frame; retrying...", file=sys.stderr)
                time.sleep(0.1)
                continue

            total_frames += 1
            infer_ms, detections = process_frame(
                frame, session, input_name, args, class_names, allowed_classes, total_frames
            )
            infer_times.append(infer_ms)

            if detections:
                det_frames += 1
            else:
                if time.time() - last_no_ball_log >= 5.0:
                    now = time.strftime("%H:%M:%S")
                    print(f"[{now}] frame {total_frames}: no balls")
                    last_no_ball_log = time.time()

            if show:
                for d in detections:
                    color = pick_color(d["name"])
                    pt1 = (int(d["x1"]), int(d["y1"]))
                    pt2 = (int(d["x2"]), int(d["y2"]))
                    cv2.rectangle(frame, pt1, pt2, color, 2)
                    label = f"{d['name']} {d['conf']:.2f}"
                    cv2.putText(
                        frame,
                        label,
                        (int(d["x1"]), max(15, int(d["y1"]) - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.5,
                        color,
                        1,
                    )
                cv2.imshow("ball_detector", frame)
                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break

            if args.max_frames and total_frames >= args.max_frames:
                break
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        if show:
            cv2.destroyAllWindows()

    avg_ms = np.mean(infer_times) if infer_times else 0.0
    print(
        f"summary: {total_frames} frames, {det_frames} with balls, "
        f"avg inference {avg_ms:.1f} ms/frame"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
