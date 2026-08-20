# Nepal Bird ID

![Nepal Bird ID](assets/nepal-bird-hero.webp)

Identify and explore 85 birds through an accessible, explainable AI experience
created for Nepal.

This mobile-first Streamlit website reports the top three matches from a custom
EfficientNetB0 model, creates an optional Grad-CAM attention map, and includes a
searchable visual guide to the model's complete bird library.

This is an independent biodiversity-learning prototype. Merlin Bird ID
inspired the clarity of the single-photo workflow, but this project does not
copy its interface or branding and is not affiliated with Merlin or the
Cornell Lab of Ornithology.

## What happens when someone uploads a photo

1. The image is corrected for camera orientation, converted to RGB and resized
   to 224 × 224.
2. The already-trained weights in `new_best_efficientnetb0.h5` run inference.
   No training happens on the website.
3. The site displays the strongest match and two alternatives.
4. If requested, Grad-CAM highlights regions that influenced the strongest
   match. This is an interpretation aid, not evidence that the answer is right.

Uploaded photographs are not added to the training dataset by this code.

## Run locally

Use Python 3.11. On macOS, a clean virtual environment avoids mixing TensorFlow
with packages from an older Anaconda installation.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

On Windows, activate with `.venv\Scripts\activate` instead.

## Publish on Streamlit Community Cloud

1. Create an empty GitHub repository. Do not upload the model through GitHub's
   browser page: browser uploads are limited to 25 MiB. The 34 MB model is
   allowed when pushed with Git or GitHub Desktop because it is below GitHub's
   100 MiB repository limit.
2. In Terminal, open this project folder and push it with Git:

   ```bash
   git init
   git add .
   git commit -m "Initial Nepal Bird ID website"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPOSITORY.git
   git push -u origin main
   ```

   Replace the final URL with the URL of your empty repository. If GitHub asks
   you to authenticate, sign in through the browser prompt or use GitHub Desktop.
3. Confirm that the repository contains `app.py`, `requirements.txt`,
   `.python-version`, `.streamlit/config.toml`, `class_names.json`, `assets/`
   and the model weights.
4. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) using
   the GitHub account that can read the repository.
5. Select **Create app**, choose the repository and branch, and set the entry
   point to `app.py`.
6. Choose an available `streamlit.app` subdomain, then deploy.

The first visit can take longer while TensorFlow and the model start. Later
predictions reuse Streamlit's cached model resource.

## Project structure

- `app.py` — responsive website and interaction flow
- `bird_guide.py` — searchable guide interface and attributed Commons photos
- `bird_catalog.py` — taxonomy and report-based status metadata
- `model_utils.py` — model reconstruction, preprocessing, inference and Grad-CAM
- `class_names.json` — exact 85-class order used during training
- `new_best_efficientnetb0.h5` — final trained weights
- `assets/` — optimized brand and social-preview artwork
- `.streamlit/config.toml` — theme and minimal production toolbar
- `requirements.txt` — pinned runtime packages

## Honest limitations

- The model always chooses among its 85 learned classes, even for a non-bird or
  an unsupported species.
- Softmax output is a relative model score, not a calibrated real-world
  probability.
- Grad-CAM shows influential pixels but cannot prove the model used valid
  biological features.
- Before making an accuracy claim, evaluate on a separate, duplicate-free test
  set collected outside the training folders.
- The guide reproduces taxonomy and threat fields from the project's
  2022-checklist-based report; those fields should not be treated as a live
  conservation database. Nepali names, range and season still need a reviewed
  authoritative source before being added.

## Verified

The saved weights load into the reconstructed EfficientNetB0 architecture with
input shape `(None, 224, 224, 3)` and output shape `(None, 85)`. Prediction and
Grad-CAM both complete successfully on CPU. The Streamlit app also passes a
headless startup test with no application exceptions.
