# Engine

    python3 engine/gridzilla_engine.py --plan     # what is switched on
    python3 engine/gridzilla_engine.py --fetch    # writes out/engine-output.json

Then open the app, go to Sources, and press "Import engine output".

Standard library only, except `lbnl_queued_up`, which needs one package:

    pip install -r engine/requirements.txt

API keys come from the environment, never from the config file:

    export GRIDZILLA_EIA_OPEN_DATA_KEY=...

Switch sources on in the app, press "Copy sources.yaml", and paste it over
`config/sources.yaml`. Sources with `mode: engine` and no connector yet are
listed by `--plan` as "no connector yet" so you always know what is missing.
