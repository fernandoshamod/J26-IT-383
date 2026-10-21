import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
import segmentation_models_pytorch as smp
from PIL import Image

CLASSES = [
    "room_region",
    "wall",
    "door",
    "window",
]

COLORS = np.array([
    [66, 185, 100],
    [215, 55, 60],
    [245, 167, 40],
    [55, 125, 240],
], dtype=np.uint8)


def load_image(path):
    with Image.open(path) as source:
        source.load()
        image = source.convert("RGBA")

    canvas = Image.new(
        "RGBA", image.size, (255, 255, 255, 255)
    )
    canvas.alpha_composite(image)
    return canvas.convert("RGB")


def load_model(checkpoint_path, device):
    checkpoint = torch.load(
        checkpoint_path,
        map_location="cpu",
        weights_only=True,
    )

    assert checkpoint["architecture"] == "Unet"
    assert checkpoint["encoder"] == "resnet18"
    assert checkpoint["classes"] == CLASSES
    assert checkpoint["size"] == 512

    model = smp.Unet(
        encoder_name="resnet18",
        encoder_weights=None,
        in_channels=3,
        classes=len(CLASSES),
    )

    # Strict loading: missing or incompatible weights
    # must fail instead of silently generating predictions.
    model.load_state_dict(
        checkpoint["model"],
        strict=True,
    )

    model.to(device)
    model.eval()
    return model


def run(image_path, checkpoint_path, output_dir):
    image_path = Path(image_path)
    checkpoint_path = Path(checkpoint_path)
    output_dir = Path(output_dir)

    original = load_image(image_path)
    width, height = original.size

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print("Loading trained U-Net:", checkpoint_path)
    print("Device:", device)

    model = load_model(checkpoint_path, device)

    resized = original.resize(
        (512, 512),
        Image.Resampling.BILINEAR,
    )

    rgb = np.asarray(resized, dtype=np.float32)

    # Candidate preprocessing:
    # RGB channels scaled to [0,1].
    # Must be reconciled with the original training script
    # before claiming a validated inference pipeline.
    rgb = rgb / 255.0

    mean = np.array(
        [0.485, 0.456, 0.406],
        dtype=np.float32,
    )

    std = np.array(
        [0.229, 0.224, 0.225],
        dtype=np.float32,
    )

    rgb = (rgb - mean) / std

    tensor = torch.from_numpy(
        rgb.transpose(2, 0, 1).copy()
    ).unsqueeze(0).to(device)

    with torch.inference_mode():
        logits = model(tensor)
        assert logits.shape[1] == 4
        probabilities = torch.softmax(
            logits, dim=1
        )
        prediction = probabilities.argmax(
            dim=1
        )[0].cpu().numpy().astype(np.uint8)

        confidence = probabilities.max(
            dim=1
        ).values[0].cpu().numpy()

    prediction_image = Image.fromarray(prediction)
    prediction_full = prediction_image.resize(
        (width, height),
        Image.Resampling.NEAREST,
    )
    mask = np.asarray(prediction_full)

    color_image = Image.fromarray(
        COLORS[mask],
        mode="RGB",
    )

    overlay = Image.blend(
        original,
        color_image,
        alpha=0.38,
    )

    confidence_image = Image.fromarray(
        np.uint8(
            np.clip(confidence * 255, 0, 255)
        )
    ).resize(
        (width, height),
        Image.Resampling.BILINEAR,
    )

    digest = hashlib.sha256(
        image_path.read_bytes()
    ).hexdigest()[:16]

    run_dir = output_dir / ("unet_normalized_v2_" + digest)

    if run_dir.exists():
        raise RuntimeError(
            "Output directory exists; refusing overwrite: "
            + str(run_dir)
        )

    run_dir.mkdir(parents=True)

    original.save(run_dir / "original.png")
    color_image.save(run_dir / "prediction_color.png")
    overlay.save(run_dir / "prediction_overlay.png")
    prediction_full.save(run_dir / "class_indices.png")
    confidence_image.save(run_dir / "confidence.png")

    counts = np.bincount(
        prediction.flatten(), minlength=4
    )

    summary = {
        "source_image": str(image_path),
        "checkpoint": str(checkpoint_path),
        "device": str(device),
        "image_width": width,
        "image_height": height,
        "model_input_size": 512,
        "model_architecture": "Unet",
        "encoder": "resnet18",
        "classes": CLASSES,
        "class_pixel_counts": {
            name: int(counts[i])
            for i, name in enumerate(CLASSES)
        },
        "class_pixel_percentages": {
            name: round(
                100.0 * counts[i] / mask.size, 3
            )
            for i, name in enumerate(CLASSES)
        },
        "mean_model_confidence": round(
            float(confidence.mean()), 4
        ),
        "preprocessing": (
            "RGB resize 512x512; /255 normalization; "
            "ImageNet mean/std matched to original training script"
        ),
        "predictions_planner_verified": False,
        "geometry_extracted": False,
        "real_world_scale_verified": False,
        "safety_verified": False,
        "ground_truth_available": False,
        "outputs": {
            "original": "original.png",
            "colored_prediction": "prediction_color.png",
            "overlay": "prediction_overlay.png",
            "class_indices": "class_indices.png",
            "confidence": "confidence.png",
        },
    }

    (run_dir / "inference_report.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("=== U-NET INFERENCE COMPLETE ===")
    print("Original size:", original.size)
    print("Model output classes:", CLASSES)
    print("Predicted pixel distribution:")

    for name, percentage in summary[
        "class_pixel_percentages"
    ].items():
        print(" ", name, ":", percentage, "%")

    print(
        "Mean softmax confidence:",
        summary["mean_model_confidence"],
    )
    print("Output:", run_dir)
    print("Planner verified: NO")
    print("Training preprocessing verified: NO")
    print("Real-world geometry validated: NO")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output", required=True)
    arguments = parser.parse_args()

    run(
        arguments.image,
        arguments.checkpoint,
        arguments.output,
    )