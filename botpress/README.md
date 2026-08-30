# 🏀 HoopMind — Botpress Assistant

> Part of the [HoopMind](../README.md) multi-platform chatbot project.
> Sibling implementations: [Rasa Pro](../rasa/README.md) · [Dialogflow ES](../dialogflow-es/README.md)

The Botpress build of HoopMind is hosted on **Botpress Cloud** — there is no local server to
install and nothing to run from this directory. Open the shareable webchat link and start asking,
or import the bundled export into your own workspace to inspect the flows.

It answers from the same [dataset](#4-dataset) as the [Rasa](../rasa/README.md) and
[Dialogflow ES](../dialogflow-es/README.md) builds: 22 CSVs covering the NBA, ABA and BAA from
**1947 to 2026**, 5,367 players and 96 teams.

## 1. Botpress Webchat Preview

Open the following link to preview and test the published chatbot:

**[Open the HoopMind Botpress Webchat →](https://cdn.botpress.cloud/webchat/v3.7/shareable.html?configUrl=https://files.bpcontent.cloud/2026/08/27/19/20260827194750-N3YOHYZ0.json)**

```
https://cdn.botpress.cloud/webchat/v3.7/shareable.html?configUrl=https://files.bpcontent.cloud/2026/08/27/19/20260827194750-N3YOHYZ0.json
```

| | |
|---|---|
| **Webchat version** | v3.7 |
| **Config** | `https://files.bpcontent.cloud/2026/08/23/20/20260823204029-8F5ANTS0.json` |
| **Requirements** | A modern browser. Nothing to install. |

### Embedding it elsewhere

The same shareable page works inside an `<iframe>`:

```html
<iframe
  src="https://cdn.botpress.cloud/webchat/v3.7/shareable.html?configUrl=https://files.bpcontent.cloud/2026/08/27/19/20260827194750-N3YOHYZ0.json"
  width="100%"
  height="600"
  style="border: 0;"
  title="HoopMind Botpress webchat">
</iframe>
```

## 2. Import the Botpress Project

The export lives in this folder as **`Hoopmind.bpz.zip`** (~58 MB) — it carries the bot's flows,
knowledge base and uploaded data files.

1. Download the submitted Botpress export file in ZIP or BPZ format.
2. Do not extract the export file.
3. Sign in to [Botpress Cloud](https://app.botpress.cloud/).
4. Open a Botpress workspace.
5. Select **Create Bot** or **Import Bot**.
6. Choose **Import Bot** and upload the downloaded ZIP or BPZ file.
7. Wait for the import process to finish.
8. Open the imported bot in Botpress Studio.
9. Use the Studio emulator to test the chatbot.
10. Click **Publish** if a new Webchat version is required.

Publishing mints a **new** `configUrl`. If you republish, update the link in §1 — the one above
points at the original deployment.

## 3. Example questions

- *"Tell me about LeBron James"*
- *"How many points did Stephen Curry average in 2016?"*
- *"Compare Kobe and Jordan career scoring"*
- *"Was Dirk an All-Star in 2010?"*
- *"Who was the first overall pick in 2003?"*
- *"Who won MVP in 2016?"*

## 4. Dataset

**[NBA / ABA / BAA Stats](https://www.kaggle.com/datasets/sumitrodatta/nba-aba-baa-stats)** by
Sumitro Datta on Kaggle, scraped from
[Basketball Reference](https://www.basketball-reference.com/) — the same 22 CSVs the other two
implementations use.

| | |
|---|---|
| **Files** | 22 CSVs (~32 MB) |
| **Seasons** | 1947 – 2026 |
| **Leagues** | NBA, ABA, BAA |
| **Players** | 5,367 |
| **Teams** | 96 |

The data is uploaded into the Botpress Cloud workspace rather than vendored as loose CSVs here,
which is why this directory has no `data/` folder — the export carries its own copy, and the
local builds keep theirs in [`rasa/data/nba/`](../rasa/data/nba/) and
[`dialogflow-es/data/`](../dialogflow-es/data/).

## 5. Notes

- The bot logic lives in the Botpress Cloud workspace. This directory holds the webchat link plus
  the `.bpz` export — there is no source to run locally.
- Because the webchat is a hosted link, the version behind it can change without a commit here.
  If the link stops resolving, republish the bot from Botpress Studio and update the `configUrl`
  in §1.
- Refreshing the dataset means re-uploading it in Botpress Studio — it is not picked up from this
  repository the way the Rasa and Dialogflow builds pick up their local copies.

## 6. Credits

- Platform: [Botpress](https://botpress.com/)
- Data: [NBA / ABA / BAA Stats](https://www.kaggle.com/datasets/sumitrodatta/nba-aba-baa-stats)
  by Sumitro Datta, via [Basketball Reference](https://www.basketball-reference.com/)
