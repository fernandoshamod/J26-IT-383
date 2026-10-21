"""Portable inference/evidence replay for the frozen Component 1 V3 checkpoint.

No training entrypoint. Original research modules are never imported or edited.
"""
from pathlib import Path
import hashlib
import json
import os
import time

CLASSES = ['room_region', 'wall', 'door', 'window']
COLORS = [[66, 185, 100], [215, 55, 60], [245, 167, 40], [55, 125, 240]]
CHECKPOINT_SHA256 = '352631590f1610b6b29341b3d1c59fad2ad564ed07fa4b77c9c59470bfde5c0c'


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def verify_assets(root):
    root = Path(root).resolve()
    manifest = read(root / 'ASSET_HASHES.json')
    for rel, expected in manifest.items():
        path = (root / rel).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError('Missing or unsafe asset: ' + rel)
        if sha256(path) != expected:
            raise ValueError('Asset identity mismatch: ' + rel)
    return {'status': 'PASS', 'immutable_assets_checked': len(manifest)}


def load_model(root, device='auto'):
    # Prevent pretrained-weight fetching; dependency installation is a separate cell.
    os.environ.setdefault('HF_HUB_OFFLINE', '1')
    os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')
    import torch
    import segmentation_models_pytorch as smp
    root = Path(root)
    path = root / '04_MODEL_CHECKPOINT/best_native_unet.pt'
    if sha256(path) != CHECKPOINT_SHA256:
        raise ValueError('Frozen checkpoint hash mismatch; do not replace it.')
    checkpoint = torch.load(path, map_location='cpu', weights_only=True)
    for key, value in {'architecture': 'Unet', 'encoder': 'resnet18',
                       'classes': CLASSES, 'size': 512, 'ignore_index': 255}.items():
        if checkpoint.get(key) != value:
            raise ValueError('Checkpoint metadata mismatch: ' + key)
    device = torch.device(('cuda' if torch.cuda.is_available() else 'cpu')
                          if device == 'auto' else device)
    model = smp.Unet(encoder_name='resnet18', encoder_weights=None,
                     in_channels=3, classes=4)
    model.load_state_dict(checkpoint['model'], strict=True)
    model.to(device).eval()
    metadata = {key: checkpoint[key] for key in
                ['architecture', 'encoder', 'classes', 'size', 'ignore_index',
                 'epoch', 'val_miou', 'imagenet_init_sha256']}
    return model, device, metadata


def preprocess(path):
    """Same letterbox and RGB/ImageNet operation as native_data + V4 upload path."""
    import numpy as np
    import torch
    from PIL import Image
    with Image.open(path) as source:
        source.load()
        if source.width * source.height > 16_000_000:
            raise ValueError('Example interface limited to 16 million source pixels.')
        # Uploaded transparency is composited onto white; RGB included example unchanged.
        rgba = source.convert('RGBA')
        canvas = Image.new('RGBA', rgba.size, (255, 255, 255, 255))
        canvas.alpha_composite(rgba)
        original = canvas.convert('RGB')
    w, h = original.size
    scale = min(512 / w, 512 / h)
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    left, top = (512 - nw) // 2, (512 - nh) // 2
    image = Image.new('RGB', (512, 512), 'white')
    image.paste(original.resize((nw, nh), Image.Resampling.BILINEAR), (left, top))
    array = np.array(image, np.float32) / 255
    array = (array - np.array([.485, .456, .406], np.float32)) / np.array([.229, .224, .225], np.float32)
    tensor = torch.from_numpy(array.transpose(2, 0, 1).copy()).unsqueeze(0)
    return original, image, tensor, {'original_wh': [w, h], 'resized_wh': [nw, nh],
                                   'offset_xy': [left, top], 'model_size': 512}


def predict(model, device, source, out):
    """One real FP32 forward; returns unapproved pixel labels, never a metric Twin."""
    import numpy as np
    import torch
    from PIL import Image
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    original, image, tensor, transform = preprocess(source)
    tensor = tensor.to(device)
    if device.type == 'cuda':
        torch.cuda.synchronize(device)
    started = time.perf_counter()
    with torch.inference_mode():
        logits = model(tensor)
        if tuple(logits.shape) != (1, 4, 512, 512):
            raise ValueError('Unexpected model output shape')
        mask = logits.argmax(1)[0].cpu().numpy().astype(np.uint8)
    if device.type == 'cuda':
        torch.cuda.synchronize(device)
    seconds = time.perf_counter() - started
    left, top = transform['offset_xy']
    nw, nh = transform['resized_wh']
    full = Image.fromarray(mask[top:top + nh, left:left + nw]).resize(original.size, Image.Resampling.NEAREST)
    color = Image.fromarray(np.array(COLORS, np.uint8)[np.array(full)])
    original.save(out / 'SOURCE_DECODED.png')
    image.save(out / 'INPUT_LETTERBOX_512.png')
    Image.fromarray(mask).save(out / 'PREDICTION_512.png')
    full.save(out / 'PREDICTION_ORIGINAL_PIXELS.png')
    color.save(out / 'PREDICTION_COLOR.png')
    Image.blend(original, color, .35).save(out / 'OVERLAY.png')
    result = {'status': 'PREDICTION_ONLY_REVIEW_REQUIRED', 'checkpoint_sha256': CHECKPOINT_SHA256,
              'source_sha256': sha256(source), 'source_name': Path(source).name,
              'device': str(device), 'input_shape': list(tensor.shape),
              'logits_shape': list(logits.shape), 'dtype': str(logits.dtype),
              'forward_argmax_transfer_seconds': seconds, 'warmup_forwards': 0,
              'measured_forwards': 1, 'transform': transform,
              'class_indices': dict(enumerate(CLASSES)), 'optimization_ready': False,
              'metric_calibration': None, 'planner_approval': None,
              'protocol': 'U-Net only; no YOLO, confidence filtering, components, Twin or optimizer.',
              'artifacts': {p.name: sha256(p) for p in out.glob('*.png')}}
    (out / 'RESULT.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def plot_training(root, out):
    """Plot saved observations only. No model imports or training required."""
    import numpy as np
    import matplotlib.pyplot as plt
    root, out = Path(root), Path(out)
    out.mkdir(parents=True, exist_ok=False)
    h = read(root / '02_ORIGINAL_TRAINING_EVIDENCE/history.json')
    evaluation = read(root / '02_ORIGINAL_TRAINING_EVIDENCE/EVALUATION.json')
    train, val = ([x for x in h if x['phase'] == phase] for phase in ['train', 'val'])
    best = max(val, key=lambda x: x['miou'])
    paths = []
    for field, title in [('loss', 'Observed epoch loss'), ('miou', 'Observed pooled four-class mIoU')]:
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
        for ax, rows, label in zip(axes, [train, val], ['Training (augmented)', 'Validation (no augmentation)']):
            ax.plot([x['epoch'] for x in rows], [x[field] for x in rows], 'o-', color='#087f83')
            ax.set(title=label, xlabel='Epoch', ylabel=field, xticks=[1, 4, 8, 12, 16])
            ax.grid(alpha=.2)
        axes[1].axvline(best['epoch'], ls='--', color='#b26418', label='Chosen checkpoint: epoch 13')
        axes[1].legend(fontsize=8)
        fig.suptitle(title + ' | saved 16-epoch run')
        fig.tight_layout()
        path = out / (field + '_curves.png'); fig.savefig(path, dpi=220); plt.close(fig); paths.append(path)
    metrics = evaluation['native_v3']['native']['pooled_metrics']
    fig, ax = plt.subplots(figsize=(8, 4.5))
    values = metrics['class_iou']; bars = ax.bar(CLASSES, values, color=np.array(COLORS) / 255)
    ax.set(ylim=(0, 1.12), ylabel='Pooled IoU', title='V3 native diagnostic_test | 64 historically exposed source families')
    ax.bar_label(bars, labels=[f'{x:.4f}' for x in values]); fig.tight_layout()
    path = out / 'native_diagnostic_class_iou.png'; fig.savefig(path, dpi=220); plt.close(fig); paths.append(path)
    fig, ax = plt.subplots(figsize=(7, 5.4))
    cm = np.array(evaluation['native_v3']['native']['pooled_confusion'])
    im = ax.imshow(cm / cm.sum(1, keepdims=True), vmin=0, vmax=1, cmap='Blues')
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f'{cm[i,j]:,}', ha='center', va='center', fontsize=9,
                    color='white' if cm[i,j] / cm[i].sum() > .55 else 'black')
    ax.set(xticks=range(4), yticks=range(4), xticklabels=CLASSES, yticklabels=CLASSES,
           xlabel='Prediction', ylabel='Ground truth', title='Native diagnostic confusion | valid pixels only')
    plt.setp(ax.get_xticklabels(), rotation=20, ha='right'); fig.colorbar(im, ax=ax, label='Row proportion')
    fig.tight_layout(); path = out / 'native_confusion.png'; fig.savefig(path, dpi=220); plt.close(fig); paths.append(path)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    native = metrics['class_iou']; cvc = evaluation['native_v3']['observed_cvc']['pooled_metrics']['class_iou']
    xx = np.arange(4); ax.bar(xx-.18, native, .36, label='Native diagnostic (64)'); ax.bar(xx+.18, cvc, .36, label='Previously observed CVC (10)')
    ax.set(xticks=xx, xticklabels=CLASSES, ylim=(0, 1.12), ylabel='IoU', title='Different domains/ontologies; not a controlled causal delta')
    ax.legend(); fig.tight_layout(); path = out / 'domain_diagnostics.png'; fig.savefig(path, dpi=220); plt.close(fig); paths.append(path)
    return paths
