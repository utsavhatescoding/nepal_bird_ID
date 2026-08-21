# Nepal Bird ID

This Streamlit app wraps the EfficientNetB0 model from `Bird_ID1.ipynb`.
It accepts one bird photograph and presents three visual matches with model
scores, attributed reference photographs, an 85-species guide and Grad-CAM.

## What you need

- Python 3.12 (the deployment target)
- This project folder

The trained `new_best_efficientnetb0.h5` weights are included. The training
image ZIP is **not required**. The exact 85-class mapping from the notebook is
already stored in `class_names.json`.

## Set up on macOS or Windows

1. Open Terminal (macOS) or Command Prompt/PowerShell (Windows) in this folder.
2. Create and activate a virtual environment.

macOS:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Windows:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
```

3. Install and run:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Your browser should open at `http://localhost:8501`.

## Product behaviour

- JPG, JPEG/JFIF, PNG, WebP, HEIC/HEIF, BMP and TIFF uploads are accepted.
- The original photograph is used by default. Optional centre-focus mode crops
  the outer frame locally; no user photograph is sent to a background-removal API.
- Prediction and Grad-CAM use the same selected image version.
- Species photographs come from Wikimedia Commons with creator, licence and
  source attribution.
- Species overview text is requested from Wikipedia with a source link. If the
  request is unavailable, the taxonomy profile still works.
- Taxonomy and threatened-status fields reproduce the supplied project report
  and are clearly marked as report-derived rather than live conservation data.

## Contributor photographs

Until portraits are supplied, the Mission page shows polished initial-based
placeholders. Later, add the images below; WebP, JPG, JPEG and PNG are supported:

- `assets/contributors/prajwol-karki.webp`
- `assets/contributors/utsav-phuyal.webp`
- `assets/contributors/bibha-sss.webp`

## Important limitations

- The model always chooses among 85 classes, even when the uploaded image is
  not a bird or contains a bird outside those classes.
- The shown confidence is a softmax model score and is not calibrated as a
  real-world probability.
- The notebook tested an image from the same dataset and called it "unseen";
  this does not establish reliable real-world accuracy. Test the app with a
  separate, duplicate-free test set before making accuracy claims.
- Internet access is required for live Wikimedia photographs and Wikipedia
  profile text. Prediction itself uses the local H5 weights.

## Project files

- `app.py` — Streamlit interface
- `model_utils.py` — model architecture, preprocessing, and prediction
- `bird_guide.py` — species profiles, descriptions and attributed photographs
- `bird_catalog.py` — report-derived taxonomy and status mapping
- `SOURCES.md` — public source, licence and model-scope notes
- `class_names.json` — exact Keras class-index order from the notebook
- `new_best_efficientnetb0.h5` — trained model weights
- `requirements.txt` — Python dependencies

## Verification completed

The weights were loaded with TensorFlow 2.20.0 into the reconstructed model.
The verified model input is `(None, 224, 224, 3)`, its output is `(None, 85)`,
and a full preprocessing-and-prediction pass completed successfully.
