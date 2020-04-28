# pulls dashboard
Dashboard for systematic view of pull requests of a selected repository

By now you have to have variable GITHUB_TOKEN set in the environment, otherwise you may exceed allowed limit for not authenticated requests ("https://developer.github.com/v3/#rate-limiting")

To run locally:
``` console
export FLASK_APP=pulls_dashboard.py

flask run
```

Then open localhost
