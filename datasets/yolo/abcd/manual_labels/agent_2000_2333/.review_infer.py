from pathlib import Path
import json
from ultralytics import YOLO

ROOT = Path("datasets/yolo/abcd")
OUT = ROOT / "manual_labels" / "agent_2000_2333"
paths = [ROOT / "images" / f"map_{i:04d}.jpg" for i in range(2000, 2334)]
model = YOLO("runs/abcd/train2/weights/best.pt")
rows = []
for result in model.predict(
    source=[str(p) for p in paths],
    conf=0.12,
    iou=0.5,
    imgsz=640,
    device=0,
    verbose=False,
    stream=True,
):
    dets = []
    if result.boxes is not None:
        for xyxy, cls, conf in zip(
            result.boxes.xyxy.tolist(),
            result.boxes.cls.tolist(),
            result.boxes.conf.tolist(),
        ):
            dets.append({
                "cls": int(cls),
                "conf": float(conf),
                "xyxy": [float(v) for v in xyxy],
            })
    dets.sort(key=lambda d: (d["cls"], -d["conf"]))
    rows.append({"name": Path(result.path).name, "detections": dets})
rows.sort(key=lambda r: int(Path(r["name"]).stem.split("_")[1]))
(OUT / ".model_candidates.json").write_text(
    json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("images", len(rows), "images_with_det", sum(bool(r["detections"]) for r in rows))
for c in range(4):
    vals = [d["conf"] for r in rows for d in r["detections"] if d["cls"] == c]
    print("class", c, "boxes", len(vals), "min", min(vals) if vals else None, "max", max(vals) if vals else None)
for r in rows:
    if r["detections"]:
        print(r["name"], " ".join(f'{d["cls"]}:{d["conf"]:.3f}' for d in r["detections"]))
