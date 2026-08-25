#!/usr/bin/env python
"""Test NLU predictions directly using the NLU runner."""
import os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from rasa.engine.graph import GraphSchema, GraphComponent
from rasa.engine.runner.dask import DaskGraphRunner
from rasa.engine.storage.local_model_storage import LocalModelStorage
from rasa.shared.nlu.training_data.message import Message

model_path = "models/nlu-20260824-002705-ragged-curve.tar.gz"
storage = LocalModelStorage.create("nlu_test_storage")
metadata, runner = _load_model(model_path, storage)
