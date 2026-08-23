HoopMind Dialogflow ES resources generated from the uploaded Kaggle dataset.

Entities:
player, team, season, stat, position, award, league.

Intents:
player information/career, season/career statistics, advanced/shooting/per-36/per-100/play-by-play,
awards, All-Star, end-of-season teams, draft, team information/statistics/summaries/opponent stats,
player/team comparisons, league information, and dataset scope.

The uploaded dataset contains BAA, NBA and ABA records. If HoopMind must answer NBA-only questions,
filter the backend data by lg = NBA.

The intents have webhookState enabled because the Flask webhook should retrieve the actual statistic
from the dataset/database rather than storing thousands of static answers in Dialogflow.
