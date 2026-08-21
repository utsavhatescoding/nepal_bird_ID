# Sources, licences and data scope

## Species taxonomy and conservation fields

The model library, order/family mapping and threatened-status fields are based
on the project materials supplied by the research team. The supplied taxonomy
report describes Nepal bird records through 2022. These fields are historical
project data, not a live conservation assessment.

Before using a status for research, policy or conservation action, verify it
against the current IUCN Red List and the latest Nepal national red list.

## Bird photographs

Profile and prediction-reference photographs are requested from Wikimedia
Commons at runtime. The interface displays the creator, licence name and a link
to the original file description page. Each file has its own licence; Wikimedia
Commons does not replace the re-user's responsibility to follow it.

- Wikimedia Commons reuse guidance:
  https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia

## Species overview text

The Explore profile requests an introductory extract from English Wikipedia
through the MediaWiki Action API. The interface links to the source article and
identifies the CC BY-SA licence. If the request fails, no replacement facts are
invented; the report-derived taxonomy profile remains available.

- MediaWiki Action API: https://www.mediawiki.org/wiki/API:Action_API
- Wikipedia copyright information: https://en.wikipedia.org/wiki/Wikipedia:Copyrights

## Ecological context

The Mission page uses well-established examples of birds' ecological roles,
including seed dispersal, pollination, pest regulation and nutrient cycling.

- BirdLife International, "Why we need birds":
  https://www.birdlife.org/news/2019/01/04/why-we-need-birds-far-more-than-they-need-us/

## Model scope

The classifier must choose among its 85 trained classes. Its softmax output is
a model score, not a calibrated real-world probability. It can return a label
for an unsupported species or a non-bird image. Grad-CAM visualises influential
image regions but does not prove that the prediction is correct or biologically
meaningful.
