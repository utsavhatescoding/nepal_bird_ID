import json
import re
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps


APP_DIR = Path(__file__).resolve().parent
MODEL_PATH = APP_DIR / "new_best_efficientnetb0.h5"
CLASS_NAMES_PATH = APP_DIR / "class_names.json"
IMAGE_SIZE = (224, 224)


def load_class_names(path=CLASS_NAMES_PATH):
    with Path(path).open("r", encoding="utf-8") as file:
        names = json.load(file)
    if len(names) != 85:
        raise ValueError(f"Expected 85 class names, found {len(names)}.")
    return names


def split_class_name(raw_name):
    """Return dataset number, common name, and scientific name."""
    match = re.match(r"^(\d+)\.(.*?)_(.+)$", raw_name.strip())
    if not match:
        return "", raw_name.strip(), ""
    number, common_name, scientific_name = match.groups()
    return number, common_name.strip(), scientific_name.strip()


def prepare_image(image):
    """Match the notebook: RGB conversion, 224x224 resize, float32 batch."""
    image = ImageOps.exif_transpose(image).convert("RGB")
    image = image.resize(IMAGE_SIZE, Image.Resampling.BILINEAR)
    array = np.asarray(image, dtype=np.float32)
    return np.expand_dims(array, axis=0)


def centre_focus_crop(image, crop_percent=12):
    """Crop equal margins to enlarge a centred subject without external APIs."""
    image = ImageOps.exif_transpose(image).convert("RGB")
    crop_percent = max(0, min(int(crop_percent), 35))
    if crop_percent == 0:
        return image

    width, height = image.size
    margin_x = int(width * crop_percent / 100)
    margin_y = int(height * crop_percent / 100)
    if width - (2 * margin_x) < 32 or height - (2 * margin_y) < 32:
        return image
    return image.crop((margin_x, margin_y, width - margin_x, height - margin_y))


def build_and_load_model(model_path=MODEL_PATH, num_classes=85):
    """Rebuild the exact notebook architecture and load its H5 weights."""
    import tensorflow as tf

    base_model = tf.keras.applications.EfficientNetB0(
        weights=None,
        include_top=False,
        input_shape=(224, 224, 3),
    )
    base_model.trainable = False

    x = tf.keras.layers.GlobalAveragePooling2D()(base_model.output)
    x = tf.keras.layers.Dense(1024, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.5)(x)
    predictions = tf.keras.layers.Dense(num_classes, activation="softmax")(x)
    model = tf.keras.Model(inputs=base_model.input, outputs=predictions)

    model_path = Path(model_path)
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model not found: {model_path.name}. Place it beside app.py."
        )
    model.load_weights(model_path)
    return model


def predict_top_k(model, image, class_names, k=3):
    import tensorflow as tf

    batch = prepare_image(image)
    batch = tf.keras.applications.efficientnet.preprocess_input(batch)
    probabilities = model.predict(batch, verbose=0)[0]

    if len(probabilities) != len(class_names):
        raise ValueError(
            f"Model returned {len(probabilities)} classes, but mapping has "
            f"{len(class_names)}."
        )

    top_indices = np.argsort(probabilities)[-k:][::-1]
    return [
        {
            "index": int(index),
            "raw_name": class_names[index],
            "confidence": float(probabilities[index]),
        }
        for index in top_indices
    ]


def _colourise_heatmap(heatmap):
    """Turn a 0-1 activation map into a high-contrast ecology palette."""
    stops = np.array([0.0, 0.28, 0.52, 0.76, 1.0], dtype=np.float32)
    colours = np.array(
        [
            [16, 35, 52],
            [19, 115, 118],
            [130, 188, 97],
            [250, 190, 63],
            [221, 76, 52],
        ],
        dtype=np.float32,
    )
    channels = [np.interp(heatmap, stops, colours[:, i]) for i in range(3)]
    return np.stack(channels, axis=-1).astype(np.uint8)


def make_gradcam_images(model, image, class_index=None, max_display_size=1200):
    """Return a Grad-CAM heatmap and overlay for one predicted class."""
    import tensorflow as tf

    batch = prepare_image(image)
    batch = tf.keras.applications.efficientnet.preprocess_input(batch)

    last_conv_layer = model.get_layer("top_conv")
    grad_model = tf.keras.Model(
        inputs=model.input,
        outputs=[last_conv_layer.output, model.output],
    )

    with tf.GradientTape() as tape:
        conv_output, predictions = grad_model(batch, training=False)
        if class_index is None:
            class_index = int(tf.argmax(predictions[0]))
        class_score = predictions[:, class_index]

    gradients = tape.gradient(class_score, conv_output)
    if gradients is None:
        raise RuntimeError("Grad-CAM gradients could not be calculated.")

    channel_weights = tf.reduce_mean(gradients, axis=(0, 1, 2))
    activation = conv_output[0]
    heatmap = tf.reduce_sum(activation * channel_weights, axis=-1)
    heatmap = tf.maximum(heatmap, 0)
    peak = tf.reduce_max(heatmap)
    heatmap = tf.where(peak > 0, heatmap / peak, tf.zeros_like(heatmap))
    heatmap = heatmap.numpy()

    original = ImageOps.exif_transpose(image).convert("RGB")
    original.thumbnail((max_display_size, max_display_size), Image.Resampling.LANCZOS)
    resized = Image.fromarray((heatmap * 255).astype(np.uint8), mode="L").resize(
        original.size,
        Image.Resampling.BILINEAR,
    )
    resized_array = np.asarray(resized, dtype=np.float32) / 255.0
    coloured = Image.fromarray(_colourise_heatmap(resized_array), mode="RGB")

    mask = Image.fromarray(
        np.clip(resized_array * 190, 0, 190).astype(np.uint8),
        mode="L",
    )
    overlay = Image.composite(coloured, original, mask)
    return coloured, overlay, int(class_index)
