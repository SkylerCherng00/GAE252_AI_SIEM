# GAE252_AI_SIEM
## Testing
- Prepare the .ini files in MsgCenter/config folder
- Create virtual environment (or using poetry, uv ...etc)
  - `python -m venv gae252team2`
- Activate virtual environment
  - MAC: `source gae252team2/bin/activate`
- Install packages according to requirement.txt
  - `pip install -r requirement.txt`
- Set up configuration and vector database
  - Run `python startup.py` provided two features:
    - to generate `config.ini` from `config.ini.template`
    - to create tables in vector database from the `src` in Qrant folder
- Run `msg_api.py` in MsgCenter first
  - `python ./MsgCenter/msg_api.py`
- Then we can test the agent
  - `python ./AIAgent/agent.py`
- To test the analysis feature, open the webpage in `./AIAgent/agent_test.html`
  - The webpage will send a request to the agent API, which will return the analysis result
