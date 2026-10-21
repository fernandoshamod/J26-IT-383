import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from PIL import Image, UnidentifiedImageError

st.set_page_config(
    page_title="Adaptive Event Layout — PP1 V2",
    page_icon="🏛️",
    layout="wide",
)

ROOT = Path(__file__).resolve().parents[1]
UPLOADS = ROOT / "assets" / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)

st.title("Adaptive Event Layout Designer")
st.caption("PP1 V2 | Floorplan-first research prototype")

st.header("Step 1 — Upload Your Venue Floorplan")

st.info(
    "Upload the actual floorplan first. "
    "Automatic structure detection and event generation "
    "are not connected in this version yet."
)

venue_name = st.text_input(
    "Venue name",
    value="AYANA Bali — Amara Ballroom",
)

source_url = st.text_input(
    "Floorplan source",
    value=(
        "https://www.ayana.com/bali/meetings/"
        "amara-ballroom/"
    ),
)

uploaded = st.file_uploader(
    "Choose floorplan image",
    type=["png", "jpg", "jpeg", "webp"],
    accept_multiple_files=False,
)

if uploaded is not None:
    data = uploaded.getvalue()

    if len(data) > 15 * 1024 * 1024:
        st.error("Image exceeds 15 MB.")
        st.stop()

    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError):
        st.error("Could not read this image.")
        st.stop()

    if image.width * image.height > 20_000_000:
        st.error("Image dimensions are too large.")
        st.stop()

    white = Image.new(
        "RGBA", image.size, (255, 255, 255, 255)
    )
    white.alpha_composite(image.convert("RGBA"))
    preview = white.convert("RGB")

    left, right = st.columns([3, 1])

    with left:
        st.subheader("Uploaded Venue Floorplan")
        st.image(
            preview,
            caption=uploaded.name,
            use_container_width=True,
        )

    with right:
        st.subheader("Image information")
        st.write("Width:", image.width, "pixels")
        st.write("Height:", image.height, "pixels")
        st.write("Original format:", image.format)
        st.write("File size:", round(len(data) / 1024, 1), "KB")

        st.warning(
            "Real-world coordinate scale is not verified. "
            "This is the uploaded source image, "
            "not an AI detection result."
        )

        if st.button(
            "Save Floorplan to Project",
            type="primary",
        ):
            digest = hashlib.sha256(data).hexdigest()

            extensions = {
                "PNG": ".png",
                "JPEG": ".jpg",
                "WEBP": ".webp",
            }
            extension = extensions.get(image.format)

            if extension is None:
                st.error("Unsupported image format.")
            else:
                stem = "venue_" + digest[:16]
                destination = UPLOADS / (stem + extension)
                metadata_path = UPLOADS / (stem + ".json")

                if not destination.exists():
                    destination.write_bytes(data)

                metadata = {
                    "venue_name": venue_name,
                    "source_url": source_url,
                    "original_filename": uploaded.name,
                    "sha256": digest,
                    "width_pixels": image.width,
                    "height_pixels": image.height,
                    "image_file": destination.name,
                    "uploaded_at_utc": (
                        datetime.now(timezone.utc).isoformat()
                    ),
                    "geometry_reviewed": False,
                    "pixel_to_metre_calibrated": False,
                    "ai_detection_completed": False,
                    "reuse_rights_verified": False,
                }

                if not metadata_path.exists():
                    metadata_path.write_text(
                        json.dumps(metadata, indent=2),
                        encoding="utf-8",
                    )

                st.session_state["venue_image_path"] = str(
                    destination
                )

                st.success("Floorplan saved successfully.")
                st.code(str(destination))

    st.divider()
    st.subheader("Next — Planner Venue Confirmation")
    st.write(
        "Next we will mark the hall boundary, "
        "entrances, movable partitions and fixed objects "
        "on this uploaded image."
    )
    st.caption(
        "Furniture generation is not implemented in "
        "this upload-only checkpoint."
    )

else:
    st.warning(
        "Please upload the downloaded floorplan image."
    )