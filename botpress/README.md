# 🏀 HoopMind — Botpress Assistant

> Part of the [HoopMind](../README.md) multi-platform chatbot project.
> Sibling implementations: [Rasa Pro](../rasa/README.md) · [Dialogflow ES](../dialogflow-es/README.md)

The Botpress build of HoopMind is hosted on **Botpress Cloud** — there is no local server to
install and nothing to run from this directory. Open the shareable webchat link and start asking.

It answers from the same [dataset](#dataset) as the [Rasa](../rasa/README.md) and
[Dialogflow ES](../dialogflow-es/README.md) builds: 22 CSVs covering the NBA, ABA and BAA from
**1947 to 2026**, 5,367 players and 96 teams.

## Try it

**[Open HoopMind on Botpress Webchat →](https://cdn.botpress.cloud/webchat/v3.7/shareable.html?configUrl=https://files.bpcontent.cloud/2026/08/23/20/20260823204029-8F5ANTS0.json)**

```
https://cdn.botpress.cloud/webchat/v3.7/shareable.html?configUrl=https://files.bpcontent.cloud/2026/08/23/20/20260823204029-8F5ANTS0.json
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
  src="https://cdn.botpress.cloud/webchat/v3.7/shareable.html?configUrl=https://files.bpcontent.cloud/2026/08/23/20/20260823204029-8F5ANTS0.json"
  width="100%"
  height="600"
  style="border: 0;"
  title="HoopMind Botpress webchat">
</iframe>
```

## Example questions

The same query set that exercises the other two implementations works here — see
[example-queries.md](../example-queries.md) for the full list.

- *"Tell me about LeBron James"*
- *"How many points did Stephen Curry average in 2016?"*
- *"Compare Kobe and Jordan career scoring"*
- *"Was Dirk an All-Star in 2010?"*
- *"Who was the first overall pick in 2003?"*
- *"Who won MVP in 2016?"*

## Dataset

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

The data is uploaded into the Botpress Cloud workspace rather than vendored here, which is why
this directory has no `data/` folder — the local copies live in
[`rasa/data/nba/`](../rasa/data/nba/) and [`dialogflow-es/data/`](../dialogflow-es/data/).

## Notes

- The bot logic lives in the Botpress Cloud workspace, not in this repository. This directory
  holds only the pointer to the deployed assistant.
- Because it is a hosted link, the version behind it can change without a commit here. If the
  link stops resolving, republish the bot from Botpress Studio and update the `configUrl` above.
- Refreshing the dataset means re-uploading it in Botpress Studio — it is not picked up from this
  repository the way the Rasa and Dialogflow builds pick up their local copies.

## Credits

- Platform: [Botpress](https://botpress.com/)
- Data: [NBA / ABA / BAA Stats](https://www.kaggle.com/datasets/sumitrodatta/nba-aba-baa-stats)
  by Sumitro Datta, via [Basketball Reference](https://www.basketball-reference.com/)
